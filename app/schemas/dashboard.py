"""Schemas for the portfolio-wide dashboard summary (Phase 4).

Aggregates the same per-company AnalysisExplanation data already computed
in Phase 2 - nothing here introduces a new source of truth, it's a
portfolio-level rollup of decisions and confidence that already exist.
"""
from pydantic import BaseModel, Field


class DecisionCounts(BaseModel):
    qualified: int = 0
    disqualified: int = 0
    insufficient_data: int = 0


class DisqualificationCategoryCounts(BaseModel):
    not_disqualified: int = 0
    genuine_negative_evidence: int = 0
    insufficient_evidence: int = 0
    collection_failure: int = 0
    source_unavailable: int = 0


class DashboardSummary(BaseModel):
    total_companies: int = Field(..., ge=0, description="Every company on file, analyzed or not")
    analyzed_companies: int = Field(..., ge=0, description="Companies with at least one completed analysis")
    by_decision: DecisionCounts
    by_disqualification_category: DisqualificationCategoryCounts
    avg_confidence: float = Field(..., ge=0.0, le=1.0)
    avg_coverage: float = Field(..., ge=0.0, le=1.0)
    avg_purchase_score: float = Field(..., ge=0.0, le=100.0)
    high_priority_count: int = Field(
        ..., ge=0, description="Qualified companies with a purchase score >= the high-priority threshold"
    )
