"""Request/response schemas for the REST API."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.analysis_job import JobStatus
from app.schemas.recommendation import RecommendationResult
from app.schemas.score import PurchaseScoreResult


class AnalyzeRequest(BaseModel):
    domain: str = Field(..., description="Company domain, e.g. 'acme.com'")
    name: str | None = Field(default=None, description="Company display name, defaults to domain")


class AnalyzeJobAccepted(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    status_url: str


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    company_domain: str
    company_id: uuid.UUID | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class AnalyzeResponse(BaseModel):
    company_id: uuid.UUID
    domain: str
    purchase_score: PurchaseScoreResult
    recommendation: RecommendationResult


class CompanySummary(BaseModel):
    id: uuid.UUID
    name: str
    domain: str
    industry: str | None
    created_at: datetime
    last_processed_at: datetime | None
    purchase_score: float | None = Field(default=None, description="Latest purchase-propensity score, if analyzed")
    final_decision: str | None = Field(
        default=None, description="qualified / disqualified / insufficient_data, if analyzed"
    )
    disqualification_category: str | None = None
    confidence: float | None = Field(default=None, description="Overall confidence from the latest explanation")
    coverage_percentage: float | None = None

    model_config = {"from_attributes": True}


class CompanyListResponse(BaseModel):
    items: list[CompanySummary]
    total: int
    limit: int
    offset: int
