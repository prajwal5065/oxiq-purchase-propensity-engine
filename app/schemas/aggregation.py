"""Pydantic schemas for the SignalAggregator's output.

This is the layer that turns a flat list of evidence into the grouped view
the spec's Stage 5/7 calls for: how much evidence exists per category, how
fresh and confident it is, and which sources were actually checked versus
which failed or came back empty. Nothing here is persisted yet (Phase 1) -
it's computed on read from the Evidence Store and returned alongside the
analysis result, ready for the dashboard/API work in a later phase to
surface directly instead of recomputing.
"""
from pydantic import BaseModel, Field


class SignalGroup(BaseModel):
    category: str
    signal_count: int = Field(..., ge=0)
    avg_confidence: float = Field(..., ge=0.0, le=1.0)
    freshness: float = Field(..., ge=0.0, le=1.0, description="Mean time-decay weight of evidence in this group")
    strength: float = Field(
        ..., ge=0.0, le=1.0, description="Composite of confidence, freshness, and volume - how strong is this group"
    )


class EvidenceCoverageSummary(BaseModel):
    company_domain: str
    total_evidence: int = Field(..., ge=0)
    sources_checked: dict[str, bool] = Field(
        default_factory=dict, description="Collector name -> whether it returned live, error-free signals"
    )
    category_groups: list[SignalGroup] = Field(default_factory=list)
    overall_coverage: float = Field(..., ge=0.0, le=1.0, description="Fraction of known collectors that returned signals")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Mean confidence across all evidence")
