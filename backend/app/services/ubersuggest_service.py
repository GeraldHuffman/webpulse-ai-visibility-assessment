"""Ubersuggest MCP Service - pulls real SEO/keyword data via the Ubersuggest MCP server.

This service connects to the Ubersuggest MCP endpoint to get real data:
- Domain overview (traffic, keywords, DA, backlinks)
- Top keywords
- Competitor analysis
- Backlinks overview

The data is used to enrich the AI Visibility Assessment with real metrics
instead of hypothetical estimates.
"""

import json
from typing import Any

import httpx
from loguru import logger

from app.core.config import get_settings

settings = get_settings()

MCP_URL = "https://ubersuggest-mcp.neilpatelapi.com/mcp"


async def _call_mcp(tool_name: str, arguments: dict) -> dict | list | None:
    """Call an Ubersuggest MCP tool and return the parsed result."""
    if not settings.ubersuggest_access_token:
        logger.warning(f"Ubersuggest MCP skipped: no access token")
        return None

    try:
        resp = await httpx.AsyncClient(timeout=60.0).post(
            MCP_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments}
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {settings.ubersuggest_access_token}",
            },
        )

        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                d = json.loads(line[6:])
                content = d.get("result", {}).get("content", [])
                if content:
                    text = content[0]["text"]
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return {"raw": text}
        return None
    except Exception as e:
        logger.warning(f"Ubersuggest MCP {tool_name} failed: {e}")
        return None


async def get_domain_overview(domain: str) -> dict | None:
    """Get domain overview: traffic, keywords, DA, backlinks."""
    result = await _call_mcp("domain_overview", {"domain": domain})
    if result:
        logger.info(f"Ubersuggest: {domain} - {result.get("organic", "?")} keywords, {result.get("traffic", "?")} traffic, DA {result.get("domainAuthority", "?")}")
    return result


async def get_domain_keywords(domain: str, limit: int = 10) -> list | None:
    """Get top organic keywords for a domain."""
    result = await _call_mcp("domain_keywords", {"domain": domain, "limit": limit})
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get("keywords", result.get("results", []))
    return result


async def get_backlinks_overview(domain: str) -> dict | None:
    """Get backlinks summary for a domain."""
    result = await _call_mcp("backlinks_overview", {"domain": domain})
    return result


async def get_competitors(domain: str, limit: int = 5) -> list | None:
    """Find organic competitors of a domain."""
    result = await _call_mcp("competitors", {"domain": domain, "limit": limit})
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get("competitors", [])
    return result


async def get_top_pages(domain: str, limit: int = 5) -> list | None:
    """Get top pages by traffic for a domain."""
    result = await _call_mcp("domain_top_pages", {"domain": domain, "limit": limit})
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get("pages", [])
    return result


async def collect_ubersuggest_data(domain: str, competitor_domains: list[str] | None = None) -> dict[str, Any]:
    """Collect Ubersuggest data for the target domain and competitors.

    Returns a dict with:
    - target_overview: domain overview dict
    - target_keywords: list of top keywords
    - target_backlinks: backlinks overview
    - target_top_pages: top pages list
    - competitors: list of {domain, overview} dicts
    """
    import asyncio

    domain = domain.replace("https://", "").replace("http://", "").split("/")[0].replace("www.", "")

    logger.info(f"Collecting Ubersuggest data for {domain}")

    # Collect target data in parallel
    tasks = [
        ("target_overview", get_domain_overview(domain)),
        ("target_keywords", get_domain_keywords(domain, limit=10)),
        ("target_backlinks", get_backlinks_overview(domain)),
        ("target_top_pages", get_top_pages(domain, limit=5)),
    ]

    # Add competitor overviews
    competitor_data = []
    if competitor_domains:
        for comp in competitor_domains[:3]:
            comp_domain = comp.replace("https://", "").replace("http://", "").split("/")[0].replace("www.", "")
            tasks.append(("comp_" + comp_domain, get_domain_overview(comp_domain)))

    results = {}
    gathered = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

    for i, (name, _) in enumerate(tasks):
        if isinstance(gathered[i], Exception):
            logger.warning(f"Ubersuggest {name} failed: {gathered[i]}")
            results[name] = None
        else:
            results[name] = gathered[i]

    # Organize competitor data
    competitors = []
    for name, value in results.items():
        if name.startswith("comp_") and value:
            competitors.append({"domain": name[4:], "overview": value})
    results["competitors"] = competitors

    logger.info(f"Ubersuggest data collected: target={'yes' if results.get('target_overview') else 'no'}, competitors={len(competitors)}")
    return results
