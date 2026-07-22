"""Site Analysis Engine - collects observable signals about a website.

All signals are collected via HTTP requests. No data is fabricated.
If a check fails, we record it as unknown.
"""

import asyncio
import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.services.security import get_safe_client

# The 8 AI crawler bots that matter
AI_BOTS = [
    "GPTBot",
    "ClaudeBot",
    "PerplexityBot",
    "Google-Extended",
    "Amazonbot",
    "Bytespider",
    "CCBot",
    "Applebot-Extended",
]

# Junk URL patterns from WordPress page builders
JUNK_PATTERNS = [
    "/layout_category/", "/layout_type/", "/et_tb_item_type/",
    "/et_pb_template/", "/elementor_template/", "/wp-content/uploads/",
]

# Schema types that indicate AI-readiness
VALUABLE_SCHEMA = [
    "Service", "FAQPage", "HowTo", "LocalBusiness", "ProfessionalService",
    "Review", "AggregateRating", "Person", "Article", "Product", "Offer",
]

# Generic schema types that every WordPress site has (not a competitive signal)
GENERIC_SCHEMA = ["WebPage", "WebSite", "Organization", "BreadcrumbList", "SearchAction"]

# Standard pages to check
STANDARD_PAGES = ["/about/", "/about-us/", "/team/", "/contact/", "/privacy-policy/", "/terms/"]


async def check_robots_txt(client: httpx.AsyncClient, domain: str) -> dict[str, Any]:
    """Fetch and parse robots.txt."""
    url = f"https://{domain}/robots.txt"
    result: dict[str, Any] = {"raw": None, "exists": False, "sitemap_ref": None, "ai_bot_blocks": {}}
    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            result["raw"] = resp.text
            result["exists"] = True
            # Look for sitemap reference
            sitemap_match = re.search(r"Sitemap:\s*(.+?)(?:\n|$)", resp.text, re.IGNORECASE)
            if sitemap_match:
                result["sitemap_ref"] = sitemap_match.group(1).strip()
            # Check for AI bot blocks
            for bot in AI_BOTS:
                # Look for User-agent: BOTNAME section
                pattern = rf"User-agent:\s*{re.escape(bot)}\s*\n(.*?)(?:\nUser-agent|\Z)"
                match = re.search(pattern, resp.text, re.DOTALL)
                if match:
                    block_section = match.group(1)
                    result["ai_bot_blocks"][bot] = "Disallow: /" in block_section
                else:
                    result["ai_bot_blocks"][bot] = False
        else:
            result["ai_bot_blocks"] = {bot: False for bot in AI_BOTS}
    except Exception as e:
        logger.warning(f"robots.txt check failed for {domain}: {e}")
        result["ai_bot_blocks"] = {bot: None for bot in AI_BOTS}
    return result


async def check_llms_txt(client: httpx.AsyncClient, domain: str) -> dict[str, Any]:
    """Check for llms.txt file."""
    url = f"https://{domain}/llms.txt"
    result: dict[str, Any] = {"raw": None, "exists": False, "url_count": 0, "junk_count": 0}
    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            result["raw"] = resp.text
            result["exists"] = True
            lines = [l.strip() for l in resp.text.splitlines() if l.strip()]
            url_lines = [l for l in lines if l.startswith("http")]
            result["url_count"] = len(url_lines)
            result["junk_count"] = sum(1 for u in url_lines if any(p in u for p in JUNK_PATTERNS))
    except Exception as e:
        logger.warning(f"llms.txt check failed for {domain}: {e}")
    return result


async def check_sitemap(client: httpx.AsyncClient, domain: str) -> dict[str, Any]:
    """Fetch and parse sitemap."""
    result: dict[str, Any] = {
        "exists": False, "total_urls": 0, "post_urls": 0,
        "page_urls": 0, "category_urls": 0, "sample_urls": []
    }
    for sitemap_path in ["/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml"]:
        url = f"https://{domain}{sitemap_path}"
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                result["exists"] = True
                soup = BeautifulSoup(resp.text, "xml")
                urls = soup.find_all("url")
                locs = [u.find("loc") for u in urls if u.find("loc")]
                all_urls = [loc.text.strip() for loc in locs]
                result["total_urls"] = len(all_urls)
                result["post_urls"] = sum(1 for u in all_urls if "/blog/" in u or "/post/" in u or "/articles/" in u)
                result["page_urls"] = sum(1 for u in all_urls if "/blog/" not in u and "/category/" not in u and "/tag/" not in u)
                result["category_urls"] = sum(1 for u in all_urls if "/category/" in u or "/tag/" in u)
                result["sample_urls"] = all_urls[:20]
                break
            # Check for sitemap index
            soup = BeautifulSoup(resp.text, "xml")
            sub_sitemaps = soup.find_all("sitemap")
            if sub_sitemaps:
                result["exists"] = True
                for sm in sub_sitemaps[:3]:
                    loc = sm.find("loc")
                    if loc:
                        try:
                            sub_resp = await client.get(loc.text.strip())
                            sub_soup = BeautifulSoup(sub_resp.text, "xml")
                            sub_urls = sub_soup.find_all("url")
                            result["total_urls"] += len(sub_urls)
                            sub_locs = [u.find("loc") for u in sub_urls if u.find("loc")]
                            result["sample_urls"].extend([l.text.strip() for l in sub_locs[:10]])
                        except Exception:
                            pass
                result["sample_urls"] = result["sample_urls"][:20]
                break
        except Exception as e:
            logger.debug(f"sitemap check {sitemap_path} failed: {e}")
            continue
    return result


async def check_schema(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    """Extract JSON-LD schema types from a page."""
    result: dict[str, Any] = {"types": [], "valuable_types": [], "generic_only": False}
    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for script in soup.find_all("script", type="application/ld+json"):
                types = re.findall(r'"@type"\s*:\s*"([^"]+)"', script.string or "")
                result["types"].extend(types)
            result["types"] = list(set(result["types"]))
            result["valuable_types"] = [t for t in result["types"] if t in VALUABLE_SCHEMA]
            result["generic_only"] = len(result["valuable_types"]) == 0
    except Exception as e:
        logger.debug(f"schema check failed for {url}: {e}")
    return result


async def check_http_headers(client: httpx.AsyncClient, domain: str) -> dict[str, Any]:
    """Check HTTP headers and TTFB."""
    url = f"https://{domain}/"
    result: dict[str, Any] = {"headers": {}, "http_version": None, "ttfb_ms": None}
    try:
        start = time.monotonic()
        resp = await client.head(url)
        elapsed = (time.monotonic() - start) * 1000
        result["ttfb_ms"] = round(elapsed)
        result["headers"] = dict(resp.headers)
        result["http_version"] = resp.http_version
    except Exception as e:
        logger.debug(f"HTTP header check failed: {e}")
    return result


async def check_page_existence(client: httpx.AsyncClient, domain: str) -> dict[str, Any]:
    """Check existence of standard pages."""
    result: dict[str, Any] = {}
    for page in STANDARD_PAGES:
        url = f"https://{domain}{page}"
        try:
            resp = await client.get(url)
            result[page] = resp.status_code
        except Exception:
            result[page] = None
    return result


async def check_homepage(client: httpx.AsyncClient, domain: str) -> dict[str, Any]:
    """Extract homepage content and headings."""
    url = f"https://{domain}/"
    result: dict[str, Any] = {"headings": [], "visible_text": "", "word_count": 0, "has_icp_statement": False}
    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            for h in soup.find_all(["h1", "h2"]):
                text = h.get_text(strip=True)
                if text:
                    result["headings"].append({"tag": h.name, "text": text})
            text = soup.get_text(separator=" ", strip=True)
            result["visible_text"] = text[:5000]
            result["word_count"] = len(text.split())
    except Exception as e:
        logger.debug(f"homepage check failed: {e}")
    return result


async def check_brand_mentions(client: httpx.AsyncClient, company_name: str, domain: str) -> dict[str, Any]:
    """Check off-site authority via DuckDuckGo HTML endpoint."""
    result: dict[str, Any] = {"total_results": 0, "third_party_mentions": 0, "self_mentions": 0, "sample_results": []}
    query = f'"{company_name}" -site:{domain}'
    url = "https://html.duckduckgo.com/html/"
    try:
        resp = await client.post(url, data={"q": query}, timeout=15.0)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.find_all("div", class_="result")
            result["total_results"] = len(results)
            for r in results[:10]:
                link = r.find("a", class_="result__a")
                snippet = r.find("a", class_="result__snippet")
                if link:
                    href = link.get("href", "")
                    title = link.get_text(strip=True)
                    is_self = domain.replace("www.", "") in href
                    if is_self:
                        result["self_mentions"] += 1
                    else:
                        result["third_party_mentions"] += 1
                    result["sample_results"].append({
                        "title": title,
                        "url": href[:200],
                        "is_self": is_self,
                        "snippet": snippet.get_text(strip=True)[:200] if snippet else "",
                    })
    except Exception as e:
        logger.warning(f"brand mention check failed: {e}")
    return result


async def collect_all_signals(website_url: str, company_name: str, progress_callback=None) -> dict[str, Any]:
    """Run all 10 analysis checks in parallel and return aggregated signals.

    Args:
        website_url: The target website URL
        company_name: The company name for brand mention search
        progress_callback: Optional async callable(step_name: str) for progress updates

    Returns:
        Dict of all collected signals
    """
    from urllib.parse import urlparse
    parsed = urlparse(website_url)
    domain = parsed.hostname or website_url.replace("https://", "").replace("http://", "").split("/")[0]

    async with get_safe_client() as client:
        if progress_callback:
            await progress_callback("Checking if AI tools can find your site...")

        tasks = [
            ("robots_txt", check_robots_txt(client, domain)),
            ("llms_txt", check_llms_txt(client, domain)),
            ("sitemap", check_sitemap(client, domain)),
            ("http_headers", check_http_headers(client, domain)),
            ("page_existence", check_page_existence(client, domain)),
            ("homepage", check_homepage(client, domain)),
            ("schema_homepage", check_schema(client, f"https://{domain}/")),
        ]

        gathered = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        results: dict[str, Any] = {}
        for i, (name, _) in enumerate(tasks):
            if isinstance(gathered[i], Exception):
                logger.error(f"Check {name} failed: {gathered[i]}")
                results[name] = {}
            else:
                results[name] = gathered[i]

        if progress_callback:
            await progress_callback("Analyzing your content structure...")

        if progress_callback:
            await progress_callback("Looking for your brand across the web...")

        brand = await check_brand_mentions(client, company_name, domain)
        results["brand_mentions"] = brand

    content_inventory = {
        "total_urls": results.get("sitemap", {}).get("total_urls", 0),
        "post_urls": results.get("sitemap", {}).get("post_urls", 0),
        "page_urls": results.get("sitemap", {}).get("page_urls", 0),
        "category_urls": results.get("sitemap", {}).get("category_urls", 0),
        "sample_urls": results.get("sitemap", {}).get("sample_urls", []),
    }
    results["content_inventory"] = content_inventory

    return results
