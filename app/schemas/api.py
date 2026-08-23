"""Request/response schemas for the REST API."""
import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.analysis_job import JobStatus
from app.schemas.recommendation import RecommendationResult
from app.schemas.score import PurchaseScoreResult

# A valid hostname: only letters, digits, hyphens, dots.
# No spaces, no underscores at TLD level, no bare company names.
_DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9\-\.]*[a-z0-9])?$")


class AnalyzeRequest(BaseModel):
    domain: str = Field(..., description="Company domain, e.g. 'acme.com'")
    name: str | None = Field(default=None, description="Company display name, defaults to domain")

    @field_validator("domain", mode="before")
    @classmethod
    def normalize_and_validate_domain(cls, v: str) -> str:
        # Strip whitespace and common URL parts
        v = str(v).strip()
        v = re.sub(r"^https?://", "", v, flags=re.IGNORECASE)
        v = v.rstrip("/").lower()
        # Reject anything that still contains spaces — that's a company name, not a domain
        if " " in v:
            raise ValueError(
                f"'{v}' looks like a company name, not a domain. "
                "Please enter a valid domain such as 'example.com'."
            )
        if not _DOMAIN_RE.match(v):
            raise ValueError(
                f"'{v}' is not a valid domain. "
                "Use only letters, digits, hyphens, and dots (e.g. 'acme.com')."
            )
        if "." not in v:
            raise ValueError(
                f"'{v}' has no TLD. Did you mean '{v}.com'? "
                "Please provide a full domain such as 'acme.com'."
            )
        return v



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
