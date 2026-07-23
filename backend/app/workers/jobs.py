"""Background jobs for site analysis and report generation."""

import uuid
from typing import Any

from arq.connections import RedisSettings
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.database import get_session_maker
from app.models.orm import Assessment, Report, SiteSignal, Lead
from app.services.analysis_engine import collect_all_signals
from app.services.ai_workflow import generate_report
from app.services.crm import sync_to_clickup
from app.services.email_service import send_report_ready_email

settings = get_settings()

# In-memory progress tracking (for SSE)
_progress: dict[str, dict] = {}


async def get_progress(assessment_id: str) -> dict:
    """Get current progress for an assessment (used by SSE endpoint)."""
    return _progress.get(assessment_id, {"progress": 0, "step": "queued"})


async def _progress_callback(assessment_id: str):
    """Create a progress callback for a specific assessment."""
    async def callback(step: str):
        _progress[assessment_id] = {
            "progress": min(100, _progress.get(assessment_id, {}).get("progress", 0) + 25),
            "step": step,
        }
        logger.info(f"Assessment {assessment_id}: {step}")
    return callback


async def run_assessment(ctx: dict, assessment_id: str) -> None:
    """Background job: collect site signals and generate report."""
    assessment_uuid = uuid.UUID(assessment_id)
    progress_cb = await _progress_callback(assessment_id)

    async with get_session_maker()() as db:
        # Load assessment
        result = await db.execute(select(Assessment).where(Assessment.id == assessment_uuid))
        assessment = result.scalar_one_or_none()
        if not assessment:
            logger.error(f"Assessment {assessment_id} not found")
            return

        # Update status
        assessment.status = "analyzing"
        await db.commit()

        try:
            # Step 1: Collect signals
            await progress_cb("Checking if AI tools can find your site...")
            signals_data = await collect_all_signals(
                assessment.website_url,
                assessment.company_name,
                progress_callback=progress_cb,
            )

            # Save signals
            signal = SiteSignal(
                assessment_id=assessment_uuid,
                robots_txt=signals_data.get("robots_txt", {}).get("raw"),
                ai_bot_access=signals_data.get("robots_txt", {}).get("ai_bot_blocks", {}),
                llms_txt=signals_data.get("llms_txt", {}).get("raw"),
                llms_txt_exists=signals_data.get("llms_txt", {}).get("exists", False),
                llms_txt_url_count=signals_data.get("llms_txt", {}).get("url_count", 0),
                llms_txt_junk_count=signals_data.get("llms_txt", {}).get("junk_count", 0),
                sitemap_urls=signals_data.get("sitemap", {}),
                schema_types=signals_data.get("schema_homepage", {}).get("types", []),
                http_headers=signals_data.get("http_headers", {}).get("headers", {}),
                page_existence=signals_data.get("page_existence", {}),
                homepage_content=signals_data.get("homepage", {}).get("visible_text", ""),
                homepage_headings=signals_data.get("homepage", {}).get("headings", []),
                brand_mentions=signals_data.get("brand_mentions", {}),
                content_inventory=signals_data.get("content_inventory", {}),
                ttfb_ms=signals_data.get("http_headers", {}).get("ttfb_ms"),
            )
            db.add(signal)
            await db.commit()

            # Step 2: Generate report
            await progress_cb("Generating your personalized report...")
            assessment_dict = {
                "company_name": assessment.company_name,
                "website_url": assessment.website_url,
                "email": assessment.email,
                "industry": assessment.industry,
                "target_audience": assessment.target_audience,
                "content_frequency": assessment.content_frequency,
                "traffic_sources": assessment.traffic_sources,
                "competitors": assessment.competitors,
                "goals": assessment.goals,
            }

            report_data = await generate_report(signals_data, assessment_dict)

            # Save report
            report = Report(
                assessment_id=assessment_uuid,
                visibility_score=report_data["visibility_score"],
                category_scores=report_data["category_scores"],
                summary=report_data["summary"],
                actions=report_data["actions"],
                findings=report_data["findings"],
                unknowns=report_data["unknowns"],
                methodology=report_data["methodology"],
                big_opportunity=report_data.get("big_opportunity", ""),
                current_state=report_data.get("current_state", ""),
                llm_raw_response=report_data.get("llm_raw_response"),
                llm_model=settings.openai_model,
                llm_tokens_used=report_data.get("llm_tokens_used"),
            )
            db.add(report)

            assessment.status = "completed"
            assessment.completed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            await db.commit()

            # Step 3: Sync to CRM
            await progress_cb("Saving your results...")
            try:
                await sync_to_clickup(assessment, report)
            except Exception as e:
                logger.warning(f"CRM sync failed (non-blocking): {e}")

            # Step 4: Send email
            try:
                await send_report_ready_email(assessment, report, settings)
            except Exception as e:
                logger.warning(f"Email send failed (non-blocking): {e}")

            _progress[assessment_id] = {"progress": 100, "step": "completed"}
            logger.info(f"Assessment {assessment_id} completed: score={report_data['visibility_score']}")

        except Exception as e:
            logger.error(f"Assessment {assessment_id} failed: {e}")
            assessment.status = "failed"
            await db.commit()
            _progress[assessment_id] = {"progress": 0, "step": f"failed: {str(e)[:200]}"}


class WorkerSettings:
    """ARQ worker settings."""
    functions = [run_assessment]

    @property
    def redis_settings(self):
        # Handle rediss:// (TLS) scheme from Upstash - ARQ needs redis://
        url = settings.redis_url
        if url.startswith("rediss://"):
            # ARQ/Redis supports rediss:// natively in newer versions
            # but RedisSettings.from_dsn may not - use RedisSettings directly
            from arq.connections import RedisSettings
            return RedisSettings(host=url)
        return RedisSettings.from_dsn(url)
