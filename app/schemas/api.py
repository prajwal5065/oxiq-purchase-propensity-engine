"""Request/response schemas for the REST API."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.recommendation import RecommendationResult
from app.schemas.score import PurchaseScoreResult


class AnalyzeRequest(BaseModel):
    domain: str = Field(..., description="Company domain, e.g. 'acme.com'")
    name: str | None = Field(default=None, description="Company display name, defaults to domain")


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

    model_config = {"from_attributes": True}
