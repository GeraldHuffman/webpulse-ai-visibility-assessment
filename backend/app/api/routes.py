"""FastAPI routes for the WebPulse Assessment API."""

import asyncio
import json
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.database import get_db
from app.models.orm import Assessment, Report, ScheduledCall, EmailLog
from app.models.schemas import (
    AssessmentCreate,
    AssessmentResponse,
    ScheduleCallRequest,
    WebhookCalendly,
)
from app.services.security import validate_url
from app.workers.jobs import get_progress

settings = get_settings()
router = APIRouter(prefix="/api/v1")


@router.post("/assessments", response_model=AssessmentResponse, status_code=201)
async def create_assessment(data: AssessmentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new assessment and trigger analysis."""
    # Validate URL for SSRF safety
    try:
        safe_url = validate_url(data.website_url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid URL: {e}")

    # Verify consent
    if not data.consent:
        raise HTTPException(status_code=422, detail="GDPR consent is required")

    # Create assessment
    assessment = Assessment(
        id=uuid.uuid4(),
        company_name=data.company_name,
        website_url=safe_url,
        email=data.email,
        phone=data.phone,
        industry=data.industry,
        target_audience=data.target_audience,
        content_frequency=data.content_frequency,
        traffic_sources=data.traffic_sources,
        competitors=data.competitors,
        goals=data.goals,
        consent=data.consent,
        status="created",
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)

    logger.info(f"Created assessment {assessment.id} for {assessment.company_name}")

    # Trigger background analysis (in production: enqueue ARQ job)
    # For now, we trigger it as a background task
    asyncio.create_task(_trigger_analysis(str(assessment.id)))

    return AssessmentResponse(
        id=assessment.id,
        company_name=assessment.company_name,
        website_url=assessment.website_url,
        status=assessment.status,
        created_at=assessment.created_at.isoformat(),
        completed_at=None,
    )


async def _trigger_analysis(assessment_id: str):
    """Trigger the analysis background job."""
    from app.workers.jobs import run_assessment
    try:
        await run_assessment({}, assessment_id)
    except Exception as e:
        import traceback
        logger.error(f"Background analysis failed: {e}")
        logger.error(traceback.format_exc())


@router.get("/assessments/{assessment_id}")
async def get_assessment(assessment_id: str, db: AsyncSession = Depends(get_db)):
    """Get assessment status and details."""
    try:
        aid = uuid.UUID(assessment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid assessment ID")

    result = await db.execute(select(Assessment).where(Assessment.id == aid))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    return {
        "id": str(assessment.id),
        "company_name": assessment.company_name,
        "website_url": assessment.website_url,
        "status": assessment.status,
        "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
        "completed_at": assessment.completed_at.isoformat() if assessment.completed_at else None,
    }


@router.get("/assessments/{assessment_id}/status")
async def get_status_sse(assessment_id: str):
    """SSE endpoint for live progress updates during analysis."""
    async def event_stream():
        import time
        sent_count = 0
        while True:
            progress = await get_progress(assessment_id)
            data = json.dumps(progress)
            yield f"data: {data}\\n\\n"
            sent_count += 1

            if progress.get("step") in ("completed", "failed") or progress.get("progress", 0) >= 100:
                break
            # Timeout after 120 seconds
            if sent_count > 120:
                yield f"data: {json.dumps({"progress": 0, "step": "timeout"})}\\n\\n"
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_stream, media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


@router.get("/assessments/{assessment_id}/report")
async def get_report(assessment_id: str, db: AsyncSession = Depends(get_db)):
    """Get the generated report for an assessment."""
    try:
        aid = uuid.UUID(assessment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid assessment ID")

    result = await db.execute(select(Report).where(Report.assessment_id == aid))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not ready or not found")

    return {
        "id": str(report.id),
        "assessment_id": str(report.assessment_id),
        "visibility_score": report.visibility_score,
        "category_scores": report.category_scores,
        "summary": report.summary,
        "actions": report.actions,
        "findings": report.findings,
        "unknowns": report.unknowns,
        "methodology": report.methodology,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
    }


@router.post("/assessments/{assessment_id}/schedule")
async def schedule_call(
    assessment_id: str,
    req: ScheduleCallRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a scheduled strategy call."""
    try:
        aid = uuid.UUID(assessment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid assessment ID")

    call = ScheduledCall(
        assessment_id=aid,
        scheduled_for=datetime.fromisoformat(req.scheduled_for),
        calendly_event_id=req.calendly_event_id,
        status="scheduled",
    )
    db.add(call)
    await db.commit()

    logger.info(f"Scheduled call for assessment {assessment_id}: {req.scheduled_for}")
    return {"status": "scheduled", "call_id": str(call.id)}


@router.post("/webhooks/calendly")
async def calendly_webhook(payload: dict, request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Calendly webhook events."""
    event = payload.get("event", "")
    if event == "invitee.created":
        data = payload.get("payload", {})
        email = data.get("email", "")
        event_id = data.get("event", "")
        scheduled_for = data.get("event", {}).get("start_time", "")

        # Find assessment by email (metadata would be better in production)
        result = await db.execute(
            select(Assessment).where(Assessment.email == email).order_by(Assessment.created_at.desc()).limit(1)
        )
        assessment = result.scalar_one_or_none()
        if assessment:
            call = ScheduledCall(
                assessment_id=assessment.id,
                scheduled_for=datetime.fromisoformat(scheduled_for.replace("Z", "+00:00")) if scheduled_for else datetime.now(timezone.utc),
                calendly_event_id=event_id,
                status="scheduled",
            )
            db.add(call)
            await db.commit()
            logger.info(f"Calendly webhook: call scheduled for assessment {assessment.id}")

    return {"status": "ok"}


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
