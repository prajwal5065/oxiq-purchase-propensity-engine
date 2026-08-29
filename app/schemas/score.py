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
    applied_adjustments: list[str] = Field(
        default_factory=list,
        description=(
            "Rule Engine adjustments that changed the score away from the raw "
            "weighted pillar sum (e.g. the low-capacity or low-need penalty) - "
            "surfaced so the report can show what decreased the final score, "
            "not just the pillar contributions that increased it."
        ),
    )
