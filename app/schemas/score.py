"""Pydantic schemas for scoring agent output and the aggregate purchase score."""
from pydantic import BaseModel, Field

from app.models.score import ScoreType


class PillarScore(BaseModel):
    score_type: ScoreType
    score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)


class PurchaseScoreResult(BaseModel):
    company_domain: str
    pillar_scores: list[PillarScore]
    purchase_score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_summary: list[str] = Field(default_factory=list)
    disqualified: bool = False
    disqualified_reason: str | None = None
