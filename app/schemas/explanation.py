"""Schemas for the evidence-first "explain everything" layer.

Nothing here is a new source of truth - every field is derived from data
that already exists (Evidence rows, PillarScores, CollectorResults, the
Rule Engine's decision). This module exists purely to give that derived
explanation a strongly-typed shape the API and frontend can rely on,
instead of ad hoc strings buried in `reasons` fields.
"""
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.models.score import ScoreType
from app.schemas.signal import CollectorStatus


class CollectorStatusReport(BaseModel):
    """One collector's outcome for a single analysis run."""

    source: str
    status: CollectorStatus
    is_live: bool
    signal_count: int = Field(..., ge=0)
    errors: list[str] = Field(default_factory=list)


class EvidenceCoverage(BaseModel):
    """Stage 1/7: what did we actually check, and what came of it.

    Deliberately keeps every count separate rather than collapsing to a
    single percentage - "no evidence was found" (ran fine, nothing there),
    "source was unavailable" (not configured), and "collector failed"
    (errored) are different situations that call for different follow-up.
    """

    sources_discovered: int = Field(..., ge=0, description="Distinct collector types considered")
    sources_attempted: int = Field(..., ge=0, description="Collectors actually invoked")
    sources_successful: int = Field(..., ge=0)
    sources_failed: int = Field(..., ge=0)
    sources_zero_results: int = Field(..., ge=0)
    sources_not_configured: int = Field(..., ge=0)
    evidence_items_extracted: int = Field(..., ge=0, description="Raw evidence count before normalization")
    evidence_items_accepted: int = Field(..., ge=0, description="Evidence count after normalization/dedup")
    coverage_percentage: float = Field(..., ge=0.0, le=1.0)
    collector_statuses: list[CollectorStatusReport] = Field(default_factory=list)


class ConfidenceFactor(BaseModel):
    name: str
    value: float = Field(..., ge=0.0, le=1.0)
    weight: float = Field(..., ge=0.0, le=1.0)
    description: str


class ConfidenceExplanation(BaseModel):
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    level: Literal["high", "medium", "low"]
    factors: list[ConfidenceFactor] = Field(default_factory=list)
    summary: str


class ScoreContribution(BaseModel):
    """One piece of evidence's contribution to a pillar score."""

    evidence_id: uuid.UUID | None = None
    label: str
    excerpt: str
    source: str
    points: float
    direction: Literal["positive", "negative"]


class PillarExplanation(BaseModel):
    score_type: ScoreType
    score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0.0, le=1.0)
    positive_evidence: list[ScoreContribution] = Field(default_factory=list)
    negative_evidence: list[ScoreContribution] = Field(default_factory=list)
    missing_expected_signals: list[str] = Field(
        default_factory=list, description="Expected signal phrases for this pillar that no evidence matched"
    )
    source_coverage: dict[str, int] = Field(
        default_factory=dict, description="Collector name -> count of matched evidence from that collector"
    )


class DisqualificationCategory(StrEnum):
    """Requirement #5's four-way split, so a data problem is never reported
    as a business conclusion."""

    NOT_DISQUALIFIED = "not_disqualified"
    GENUINE_NEGATIVE_EVIDENCE = "genuine_negative_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    COLLECTION_FAILURE = "collection_failure"
    SOURCE_UNAVAILABLE = "source_unavailable"


class DisqualificationExplanation(BaseModel):
    final_decision: Literal["qualified", "disqualified", "insufficient_data"]
    category: DisqualificationCategory
    primary_reason: str
    secondary_reasons: list[str] = Field(default_factory=list)
    disqualifying_rules_triggered: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    data_quality_limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommended_next_action: str


class AnalysisExplanation(BaseModel):
    """Top-level bundle returned to the frontend for a company's dossier page."""

    company_domain: str
    headline: str = Field(
        ..., description="'WHY THIS COMPANY SCORED HIGH' / '...SCORED LOW' / 'WHY WE CANNOT RECOMMEND THIS COMPANY'"
    )
    evidence_coverage: EvidenceCoverage
    confidence_explanation: ConfidenceExplanation
    pillar_explanations: list[PillarExplanation] = Field(default_factory=list)
    disqualification: DisqualificationExplanation
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
