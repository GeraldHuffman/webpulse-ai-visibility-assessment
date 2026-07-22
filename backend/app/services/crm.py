"""ClickUp CRM integration — create tasks for new leads."""

import httpx
from loguru import logger

from app.core.config import get_settings
from app.models.orm import Assessment, Report

settings = get_settings()
CLICKUP_API = "https://api.clickup.com/api/v2"


async def sync_to_clickup(assessment: Assessment, report: Report) -> str | None:
    """Create a ClickUp task for a new assessment lead.

    Returns the ClickUp task ID, or None if sync is disabled/failed.
    """
    if not settings.clickup_api_token or not settings.clickup_list_id:
        logger.info("ClickUp sync skipped: not configured")
        return None

    task_name = f"{assessment.company_name} — AI Visibility Score: {report.visibility_score}/100"

    description = f"""AI Visibility Assessment Lead

Company: {assessment.company_name}
Website: {assessment.website_url}
Email: {assessment.email}
Industry: {assessment.industry}
AI Visibility Score: {report.visibility_score}/100

Summary:
{report.summary}

Top Actions:
"""
    for action in (report.actions or [])[:3]:
        desc = action.get("description", "") if isinstance(action, dict) else str(action)
        title = action.get("title", "") if isinstance(action, dict) else ""
        description += f"  {title}: {desc}\\n"

    description += f"""
Assessment URL: {settings.app_url}/report/{assessment.id}
"""

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{CLICKUP_API}/list/{settings.clickup_list_id}/task",
            headers={"Authorization": settings.clickup_api_token, "Content-Type": "application/json"},
            json={
                "name": task_name,
                "description": description,
                "status": "Assessment Completed",
                "custom_fields": [
                    {"id": "ai_visibility_score", "value": report.visibility_score},
                ],
            },
        )
        if resp.status_code in (200, 201):
            task = resp.json()
            logger.info(f"ClickUp task created: {task.get('id')}")
            return task.get("id")
        else:
            logger.error(f"ClickUp sync failed: {resp.status_code} {resp.text[:200]}")
            return None
