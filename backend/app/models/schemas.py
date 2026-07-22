"""Pydantic schemas for API request/response validation."""

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class Industry(str, Enum):
    saas = "saas"
    agency = "agency"
    ecommerce = "ecommerce"
    professional_services = "professional_services"
    healthcare = "healthcare"
    finance = "finance"
    manufacturing = "manufacturing"
    other = "other"


class ContentFrequency(str, Enum):
    weekly = "weekly"
    monthly = "monthly"
    rarely = "rarely"
    never = "never"


class TrafficSource(str, Enum):
    google_search = "google_search"
    social_media = "social_media"
    referrals = "referrals"
    paid_ads = "paid_ads"
    email = "email"
    direct = "direct"
    ai_tools = "ai_tools"


class Goal(str, Enum):
    get_found_by_ai = "get_found_by_ai"
    get_quoted_in_ai = "get_quoted_in_ai"
    understand_visibility = "understand_visibility"
    compare_to_competitors = "compare_to_competitors"
    improve_website_for_ai = "improve_website_for_ai"


class AssessmentCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    website_url: str = Field(..., min_length=5, max_length=2048)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    industry: Industry
    target_audience: str = Field(..., min_length=5, max_length=2000)
    content_frequency: ContentFrequency
    traffic_sources: list[TrafficSource] = Field(..., min_length=1)
    competitors: list[str] = Field(default_factory=list, max_length=3)
    goals: list[Goal] = Field(..., min_length=1)
    consent: bool = Field(..., description="GDPR consent must be True")
    recaptcha_token: Optional[str] = None

    model_config = {"use_enum_values": True}


class AssessmentResponse(BaseModel):
    id: UUID
    company_name: str
    website_url: str
    status: str
    created_at: str
    completed_at: Optional[str] = None


class AnalysisStatus(BaseModel):
    assessment_id: UUID
    status: str
    progress: int = Field(0, ge=0, le=100)
    current_step: str = ""


class Finding(BaseModel):
    category: str
    status: str  # good|warning|critical
    observation: str
    what_it_means: str


class ActionItem(BaseModel):
    priority: int
    title: str
    description: str
    difficulty: str  # easy|medium|hard
    impact: str  # low|medium|high
    category: str


class ReportResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    visibility_score: int
    category_scores: dict[str, int]
    summary: str
    actions: list[ActionItem]
    findings: list[Finding]
    unknowns: list[str]
    methodology: str
    generated_at: str


class ScheduleCallRequest(BaseModel):
    scheduled_for: str
    calendly_event_id: str


class WebhookCalendly(BaseModel):
    event: str
    payload: dict
