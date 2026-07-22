"""SQLAlchemy ORM models for the WebPulse Assessment database."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(255))
    website_url: Mapped[str] = mapped_column(String(2048))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industry: Mapped[str] = mapped_column(String(100))
    target_audience: Mapped[str] = mapped_column(Text)
    content_frequency: Mapped[str] = mapped_column(String(50))
    traffic_sources: Mapped[list] = mapped_column(JSONB, default=list)
    competitors: Mapped[list] = mapped_column(JSONB, default=list)
    goals: Mapped[list] = mapped_column(JSONB, default=list)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    signals: Mapped["SiteSignal | None"] = relationship(back_populates="assessment", uselist=False)
    report: Mapped["Report | None"] = relationship(back_populates="assessment", uselist=False)
    lead: Mapped["Lead | None"] = relationship(back_populates="assessment", uselist=False)


class SiteSignal(Base):
    __tablename__ = "site_signals"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), __import__("sqlalchemy").ForeignKey("assessments.id"))
    robots_txt: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_bot_access: Mapped[dict] = mapped_column(JSONB, default=dict)
    llms_txt: Mapped[str | None] = mapped_column(Text, nullable=True)
    llms_txt_exists: Mapped[bool] = mapped_column(Boolean, default=False)
    llms_txt_url_count: Mapped[int] = mapped_column(Integer, default=0)
    llms_txt_junk_count: Mapped[int] = mapped_column(Integer, default=0)
    sitemap_urls: Mapped[dict] = mapped_column(JSONB, default=dict)
    schema_types: Mapped[list] = mapped_column(JSONB, default=list)
    http_headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    page_existence: Mapped[dict] = mapped_column(JSONB, default=dict)
    homepage_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    homepage_headings: Mapped[list] = mapped_column(JSONB, default=list)
    brand_mentions: Mapped[dict] = mapped_column(JSONB, default=dict)
    content_inventory: Mapped[dict] = mapped_column(JSONB, default=dict)
    ttfb_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    assessment: Mapped["Assessment"] = relationship(back_populates="signals")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), __import__("sqlalchemy").ForeignKey("assessments.id"))
    visibility_score: Mapped[int] = mapped_column(Integer)
    category_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    summary: Mapped[str] = mapped_column(Text)
    actions: Mapped[list] = mapped_column(JSONB, default=list)
    findings: Mapped[list] = mapped_column(JSONB, default=list)
    unknowns: Mapped[list] = mapped_column(JSONB, default=list)
    methodology: Mapped[str] = mapped_column(Text)
    llm_raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    llm_model: Mapped[str] = mapped_column(String(100), default="gpt-4o-2024-08-06")
    llm_tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    assessment: Mapped["Assessment"] = relationship(back_populates="report")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), __import__("sqlalchemy").ForeignKey("assessments.id"))
    crm_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crm_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    crm_sync_status: Mapped[str] = mapped_column(String(50), default="pending")

    assessment: Mapped["Assessment"] = relationship(back_populates="lead")


class EmailLog(Base):
    __tablename__ = "email_log"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), __import__("sqlalchemy").ForeignKey("assessments.id"))
    email_type: Mapped[str] = mapped_column(String(50))
    recipient: Mapped[str] = mapped_column(String(255))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(50), default="sent")


class ScheduledCall(Base):
    __tablename__ = "scheduled_calls"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), __import__("sqlalchemy").ForeignKey("assessments.id"))
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    calendly_event_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
