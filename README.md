# WebPulse AI Visibility Assessment

A SaaS tool that shows businesses how visible they are across AI surfaces (ChatGPT, Gemini, Claude, Perplexity, Google AI Overviews).

## Architecture

- **Frontend**: Next.js 15 + Tailwind CSS (WebPulse brand: pink #F72585, purple #7209B7, teal #00d4a1)
- **Backend**: Python FastAPI + httpx + BeautifulSoup4
- **Database**: PostgreSQL (async via asyncpg + SQLAlchemy 2.0)
- **Queue**: Redis + ARQ for background jobs
- **LLM**: OpenAI GPT-4o with structured JSON output
- **CRM**: ClickUp (API v2)
- **Email**: Resend
- **Scheduling**: Calendly

## Quick Start

```bash
# 1. Copy env files
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# 2. Run with Docker
docker-compose up --build

# 3. Or run locally
cd backend && uv pip install -e ".[dev]" && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

## Flow

1. Landing page → "Start Free Assessment"
2. Business info form (company, website, email, phone, consent)
3. Questionnaire (6 steps: industry, audience, content frequency, traffic sources, competitors, goals)
4. Processing screen with live SSE progress updates
5. Personalized report: AI Visibility Score (0-100), 10 category breakdowns, 3-5 prioritized actions, findings, unknowns
6. Strategy call CTA (Calendly embed)

## Anti-Fabrication Principles

- Only uses observable signals collected via HTTP requests
- Never fabricates facts, metrics, or findings
- Explicitly states what data is unknown
- LLM is given structured signal data only — no web browsing
- Fact-check pass cross-references every finding against raw signals
- Methodology section in every report states what was tested and limitations

## Analysis Engine (10 checks)

1. robots.txt — AI bot blocks (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, Amazonbot, Bytespider, CCBot, Applebot-Extended)
2. llms.txt — existence, URL count, junk URL detection
3. Sitemap — URL count, content breakdown
4. Schema inventory — JSON-LD types (Service, FAQ, HowTo, Review, etc.)
5. HTTP headers — HTTP version, TTFB
6. Page existence — /about/, /team/, /contact/ status codes
7. Homepage content — headings, visible text, ICP clarity
8. Content inventory — blog posts, service pages, category pages
9. Brand mentions — DuckDuckGo search for off-site authority
10. AI search presence — estimated from indirect signals

## Scoring (10 categories, /10 each, /100 total)

| Internal | User-facing label |
|---|---|
| ai_crawler_access | Can AI Tools Find Your Site? |
| llms_txt | AI Content Guide |
| structured_data | Content Structure |
| content_inventory | Content Volume & Depth |
| homepage_messaging | Clear Business Description |
| entity_signals | Credibility Signals |
| offsite_authority | External Recognition |
| contact_nap | Contact Consistency |
| page_speed | Technical Performance |
| ai_search_presence | AI Search Presence |

## WordPress Integration

Embed in WordPress page at `webpulsehq.com/ai-visibility-assessment/`:

```html
<iframe
  src="https://assess.webpulsehq.com"
  style="width:100%; border:0; min-height:800px;"
  title="AI Visibility Assessment"
  loading="lazy">
</iframe>
```

## Deployment

- Frontend: Vercel (assess.webpulsehq.com)
- Backend: Railway or Fly.io
- Database: Neon (PostgreSQL)
- Redis: Upstash
- Object Storage: Cloudflare R2

See `~/.hermes/plans/2026-07-22_webpulse-ai-visibility-assessment.md` for full architecture.
