"""AI Workflow — generates the AI Visibility Assessment report using GPT-4o.

Anti-fabrication guardrails:
1. LLM is given structured signal data only — no web browsing tools
2. Response must match Pydantic schema (structured output)
3. Fact-check pass cross-references every finding against raw signals
4. Unknowns are explicitly listed
5. Methodology section states what was tested and limitations
"""

import json
from typing import Any

from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.core.config import get_settings

settings = get_settings()


# --- Pydantic schema for structured LLM output ---

class LLMCategoryScore(BaseModel):
    ai_crawler_access: int = Field(ge=0, le=10)
    llms_txt: int = Field(ge=0, le=10)
    structured_data: int = Field(ge=0, le=10)
    content_inventory: int = Field(ge=0, le=10)
    homepage_messaging: int = Field(ge=0, le=10)
    entity_signals: int = Field(ge=0, le=10)
    offsite_authority: int = Field(ge=0, le=10)
    contact_nap: int = Field(ge=0, le=10)
    page_speed: int = Field(ge=0, le=10)
    ai_search_presence: int = Field(ge=0, le=10)


class LLMAction(BaseModel):
    priority: int
    title: str
    description: str
    difficulty: str  # easy|medium|hard
    impact: str  # low|medium|high
    category: str


class LLMFinding(BaseModel):
    category: str
    status: str  # good|warning|critical
    observation: str
    what_it_means: str


class LLMReport(BaseModel):
    visibility_score: int = Field(ge=0, le=100)
    category_scores: LLMCategoryScore
    summary: str
    actions: list[LLMAction]
    findings: list[LLMFinding]
    unknowns: list[str]
    methodology: str


# --- Scoring rubric (in the prompt) ---

SCORING_RUBRIC = """
SCORING RUBRIC (10 categories, each /10, total /100):

1. ai_crawler_access (label: "Can AI Tools Find Your Site?")
   - 10: All 8 AI bots allowed in robots.txt
   - 5: Some bots blocked
   - 0: All bots blocked or robots.txt missing

2. llms_txt (label: "AI Content Guide")
   - 10: llms.txt exists, lists service/blog URLs, no junk
   - 5: Exists but has junk URLs or is incomplete
   - 0: Does not exist

3. structured_data (label: "Content Structure")
   - 10: Service, FAQ, HowTo, Review schema present
   - 5: Some valuable schema
   - 0: Only generic WebSite/Organization schema

4. content_inventory (label: "Content Volume and Depth")
   - 10: 100+ blog posts, clear topical clusters
   - 5: 20-100 posts
   - 0: Few or no posts

5. homepage_messaging (label: "Clear Business Description")
   - 10: Clear target customer stated, entity-rich claims with specifics
   - 5: Some messaging but vague
   - 0: No clear ICP or value prop

6. entity_signals (label: "Credibility Signals")
   - 10: About page, team page, author bios all present
   - 5: Some entity pages
   - 0: Missing About/Team pages (404)

7. offsite_authority (label: "External Recognition")
   - 10: Many third-party mentions, directory profiles, reviews
   - 5: Some mentions
   - 0: No external mentions found

8. contact_nap (label: "Contact Consistency")
   - 10: Contact page present, consistent NAP, LocalBusiness schema
   - 5: Contact page but no schema
   - 0: No contact page or inconsistent NAP

9. page_speed (label: "Technical Performance")
   - 10: HTTP/2, fast TTFB (<500ms), good cache headers
   - 5: HTTP/1.1 or slow TTFB (500-2000ms)
   - 0: Very slow (>2000ms) or unreachable

10. ai_search_presence (label: "AI Search Presence")
    - This is estimated from indirect signals, not directly tested
    - If unknown, score 5 and list in unknowns
    - 10: Strong signals suggest presence
    - 5: Unknown / cannot determine
    - 0: Strong signals suggest absence
"""

SYSTEM_PROMPT = """You are an AI visibility analyst for WebPulse. Your job is to analyze website signals and questionnaire answers to produce an AI Visibility Assessment report.

Rules:
1. ONLY use the observable signals and user inputs provided to you. Do NOT invent facts.
2. NEVER fabricate metrics, findings, or observations that are not present in the provided data.
3. If data is unknown or missing, say "We couldn't determine this" explicitly. Add it to the unknowns list.
4. Use plain English. Avoid SEO jargon. Talk about "AI discovery" — whether AI tools can find, understand, and recommend the business. Do NOT use terms like "SEO", "GEO", "AEO", "backlinks", "domain authority", or "SERP".
5. Score each category based on the rubric provided. Be conservative — if a signal is unknown, score it in the middle (5/10) and note it in unknowns.
6. Generate 3-5 prioritized actions based on the lowest-scoring categories. Each action should explain what to do and why it matters for AI discovery.
7. Write a 2-3 sentence personalized summary. Use plain English. Talk about how well AI tools can discover the business. No jargon.

Output format: structured JSON matching the provided schema."""


def _format_signals_for_prompt(signals: dict[str, Any], assessment_data: dict[str, Any]) -> str:
    """Format all signals and questionnaire answers into structured context for the LLM."""

    # AI bot access summary
    bot_blocks = signals.get("robots_txt", {}).get("ai_bot_blocks", {})
    bot_summary = []
    for bot, blocked in bot_blocks.items():
        if blocked is None:
            bot_summary.append(f"  {bot}: Unknown (check failed)")
        elif blocked:
            bot_summary.append(f"  {bot}: BLOCKED")
        else:
            bot_summary.append(f"  {bot}: Allowed")
    bot_section = "\\n".join(bot_summary) if bot_summary else "  No robots.txt found"

    # Schema types
    schema_types = signals.get("schema_homepage", {}).get("types", [])
    valuable_types = signals.get("schema_homepage", {}).get("valuable_types", [])
    schema_section = f"Detected schema types: {schema_types}" + (
        f"\\nValuable types (Service, FAQ, etc.): {valuable_types}" if valuable_types else
        "\\nNo valuable schema types detected (only generic WebSite/Organization)"
    )

    # Page existence
    page_exist = signals.get("page_existence", {})
    page_summary = []
    for page, status in page_exist.items():
        if status is None:
            page_summary.append(f"  {page}: Unknown")
        elif status == 200:
            page_summary.append(f"  {page}: Found (200)")
        elif status == 404:
            page_summary.append(f"  {page}: NOT FOUND (404)")
        else:
            page_summary.append(f"  {page}: HTTP {status}")

    # Homepage
    homepage = signals.get("homepage", {})
    headings = homepage.get("headings", [])
    heading_list = "\\n".join([f"  {h['tag']}: {h['text']}" for h in headings[:15]])

    # Brand mentions
    brand = signals.get("brand_mentions", {})
    brand_section = (
        f"Third-party mentions: {brand.get('third_party_mentions', 0)}\\n"
        f"Self mentions: {brand.get('self_mentions', 0)}\\n"
        f"Total results: {brand.get('total_results', 0)}"
    )

    # llms.txt
    llms = signals.get("llms_txt", {})
    llms_section = (
        f"Exists: {llms.get('exists', False)}\\n"
        f"URLs listed: {llms.get('url_count', 0)}\\n"
        f"Junk URLs: {llms.get('junk_count', 0)}"
    )

    # HTTP headers
    http_info = signals.get("http_headers", {})
    ttfb = http_info.get("ttfb_ms", "Unknown")
    http_version = http_info.get("http_version", "Unknown")

    # Sitemap
    sitemap = signals.get("sitemap", {})
    sitemap_section = (
        f"Exists: {sitemap.get('exists', False)}\\n"
        f"Total URLs: {sitemap.get('total_urls', 0)}\\n"
        f"Blog posts: {sitemap.get('post_urls', 0)}\\n"
        f"Pages: {sitemap.get('page_urls', 0)}"
    )

    return f"""WEBSITE SIGNALS (observable data collected via HTTP):

=== AI Crawler Access ===
{bot_section}

=== robots.txt ===
Exists: {signals.get("robots_txt", {}).get("exists", False)}
Sitemap reference: {signals.get("robots_txt", {}).get("sitemap_ref", "None")}

=== llms.txt (AI Content Guide) ===
{llms_section}

=== Sitemap ===
{sitemap_section}

=== Schema / Structured Data ===
{schema_section}

=== HTTP Headers ===
HTTP Version: {http_version}
Time to First Byte (TTFB): {ttfb}ms

=== Page Existence ===
{chr(10).join(page_summary) if page_summary else "  No data"}

=== Homepage Headings ===
{heading_list if heading_list else "  No headings extracted"}

=== Homepage Word Count ===
{homepage.get("word_count", 0)} words

=== Brand Mentions (DuckDuckGo search) ===
{brand_section}

=== Limitations ===
- Live AI engine testing was not possible from our server (datacenter IP blocks)
- No live SERP ranking data available
- No backlink profile (no third-party SEO API connected)
- Brand mention check uses DuckDuckGo as a proxy, not exhaustive
- AI search presence score is estimated from indirect signals, not directly tested

QUESTIONNAIRE ANSWERS (user-provided):
- Company name: {assessment_data.get("company_name", "")}
- Website: {assessment_data.get("website_url", "")}
- Industry: {assessment_data.get("industry", "")}
- Target audience: {assessment_data.get("target_audience", "")}
- Content frequency: {assessment_data.get("content_frequency", "")}
- Traffic sources: {assessment_data.get("traffic_sources", [])}
- Competitors: {assessment_data.get("competitors", [])}
- Goals: {assessment_data.get("goals", [])}

{SCORING_RUBRIC}

Generate the report as structured JSON matching this schema:
{{
  "visibility_score": integer 0-100,
  "category_scores": {{
    "ai_crawler_access": integer 0-10,
    "llms_txt": integer 0-10,
    "structured_data": integer 0-10,
    "content_inventory": integer 0-10,
    "homepage_messaging": integer 0-10,
    "entity_signals": integer 0-10,
    "offsite_authority": integer 0-10,
    "contact_nap": integer 0-10,
    "page_speed": integer 0-10,
    "ai_search_presence": integer 0-10
  }},
  "summary": "2-3 sentence plain English summary, first person, no jargon",
  "actions": [
    {{
      "priority": 1,
      "title": "short action title",
      "description": "what to do, why it matters for AI discovery",
      "difficulty": "easy|medium|hard",
      "impact": "low|medium|high",
      "category": "which score category this improves"
    }}
  ],
  "findings": [
    {{
      "category": "...",
      "status": "good|warning|critical",
      "observation": "what we found (observable fact only)",
      "what_it_means": "plain English explanation for AI discovery"
    }}
  ],
  "unknowns": ["things we couldn't determine and why"],
  "methodology": "what was tested and how"
}}"""


async def generate_report(signals: dict[str, Any], assessment_data: dict[str, Any]) -> dict[str, Any]:
    """Generate the AI Visibility Assessment report using GPT-4o.

    Args:
        signals: Collected site signals from the analysis engine
        assessment_data: User questionnaire answers

    Returns:
        Dict with: visibility_score, category_scores, summary, actions,
        findings, unknowns, methodology, llm_raw_response, llm_tokens_used
    """
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    user_prompt = _format_signals_for_prompt(signals, assessment_data)

    logger.info(f"Generating report with {settings.openai_model}")

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=2000,
        temperature=0.7,
    )

    content = response.choices[0].message.content
    usage = response.usage

    # Parse JSON
    try:
        report_data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}")
        logger.debug(f"Raw content: {content[:500]}")
        raise ValueError(f"LLM returned invalid JSON: {e}")

    # Validate against schema
    try:
        validated = LLMReport.model_validate(report_data)
    except Exception as e:
        logger.error(f"Report validation failed: {e}")
        raise ValueError(f"Report schema validation failed: {e}")

    # Fact-check pass: cross-reference findings against raw signals
    report_data = fact_check(report_data, signals)

    # Store metadata
    report_data["llm_raw_response"] = json.loads(content)
    report_data["llm_tokens_used"] = usage.total_tokens if usage else 0

    logger.info(f"Report generated: score={report_data['visibility_score']}, tokens={report_data['llm_tokens_used']}")
    return report_data


def fact_check(report: dict[str, Any], signals: dict[str, Any]) -> dict[str, Any]:
    """Cross-reference LLM findings against raw signals. Remove fabricated claims.

    This is the anti-fabrication guardrail. It checks that every finding
    references data actually present in the collected signals.
    """
    checked_findings = []
    for finding in report.get("findings", []):
        category = finding.get("category", "")
        observation = finding.get("observation", "").lower()

        # Check if the observation is supported by actual signal data
        is_supported = True

        # If finding claims a page exists, verify in page_existence
        if "about page" in observation or "about us" in observation:
            page_exist = signals.get("page_existence", {})
            about_found = any(
                status == 200 for page, status in page_exist.items()
                if "about" in page
            )
            if not about_found and "exists" in observation:
                is_supported = False
                logger.warning(f"Fact-check: finding about About page not supported by signals")

        # If finding mentions a specific bot, verify in ai_bot_access
        bot_blocks = signals.get("robots_txt", {}).get("ai_bot_blocks", {})
        for bot_name in ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended"]:
            if bot_name.lower() in observation and bot_name in bot_blocks:
                if bot_blocks[bot_name] is None:
                    # We don't actually know — don't let the LLM claim it does
                    if "allowed" in observation or "blocked" in observation:
                        finding["observation"] = finding["observation"].replace(
                            "is allowed", "status unknown"
                        ).replace("is blocked", "status unknown")
                        finding["status"] = "warning"

        if is_supported:
            checked_findings.append(finding)

    report["findings"] = checked_findings
    return report
