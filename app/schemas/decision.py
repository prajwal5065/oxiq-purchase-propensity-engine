"""Schemas for the Decision Intelligence layer.

Everything here is derived from evidence that already exists (EvidenceItem
rows, the purchase score, the disqualification explanation) - same
philosophy as app/schemas/explanation.py: this module gives that derived
reasoning a strongly-typed shape instead of ad hoc dicts, and every finding
carries enough of a citation (evidence_id/label/excerpt/source) to be
traced back to the exact piece of evidence that produced it.
"""
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

FreshnessLabelLiteral = Literal["very_fresh", "recent", "aging", "stale", "unknown"]


class FreshnessAssessment(BaseModel):
    """One evidence item's recency, labeled and weighted consistently with
    the Urgency scorer's decay buckets (app/scoring/time_decay.py)."""

    evidence_id: uuid.UUID
    label: FreshnessLabelLiteral
    weight: float = Field(..., ge=0.0, le=1.0)
    published_at: datetime | None = None


class SourceReliability(BaseModel):
    """Per-collector reliability tier - how much a given collector's
    evidence should be trusted in general, independent of any single
    item's extraction confidence."""

    collector: str
    tier: Literal["high", "medium", "low"]
    weight: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    evidence_count: int = Field(..., ge=0)


class EvidenceConfidenceScore(BaseModel):
    """A single evidence item's composite confidence: extraction
    confidence + source reliability + freshness, blended into one
    rankable number."""

    evidence_id: uuid.UUID
    label: str
    source: str
    collector: str | None = None
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)
    source_reliability: float = Field(..., ge=0.0, le=1.0)
    freshness_weight: float = Field(..., ge=0.0, le=1.0)
    composite_confidence: float = Field(..., ge=0.0, le=1.0)


class BuyingIntentLevel(StrEnum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"
    INSUFFICIENT_DATA = "insufficient_data"


class BuyingIntentSignal(BaseModel):
    evidence_id: uuid.UUID | None = None
    label: str
    excerpt: str
    source: str
    strength: Literal["strong", "moderate", "weak"]


class BuyingIntentAssessment(BaseModel):
    level: BuyingIntentLevel
    score: float = Field(..., ge=0.0, le=1.0)
    matched_signals: list[BuyingIntentSignal] = Field(default_factory=list)
    rationale: str


class ContradictionSeverity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"


class ContradictionEvidenceRef(BaseModel):
    evidence_id: uuid.UUID | None = None
    label: str
    excerpt: str
    source: str


class ContradictionFinding(BaseModel):
    theme: str
    severity: ContradictionSeverity
    description: str
    evidence_a: ContradictionEvidenceRef
    evidence_b: ContradictionEvidenceRef


class ContradictionReport(BaseModel):
    has_contradictions: bool
    findings: list[ContradictionFinding] = Field(default_factory=list)
    summary: str


class WhyNowTrigger(BaseModel):
    evidence_id: uuid.UUID | None = None
    label: str
    excerpt: str
    source: str
    trigger_type: str
    published_at: datetime | None = None
    freshness_label: FreshnessLabelLiteral


class WhyNowExplanation(BaseModel):
    has_timing_trigger: bool
    data_sufficient: bool = Field(
        ..., description="False when there was no evidence at all to check for triggers - distinct from 'checked and found none'"
    )
    triggers: list[WhyNowTrigger] = Field(default_factory=list)
    narrative: str


class DecisionPriority(StrEnum):
    HIGH_PRIORITY = "high_priority"
    MEDIUM_PRIORITY = "medium_priority"
    LOW_PRIORITY = "low_priority"
    INSUFFICIENT_DATA = "insufficient_data"


class DecisionFactor(BaseModel):
    name: str
    value: float
    weight: float
    description: str


class DecisionRecommendation(BaseModel):
    priority: DecisionPriority
    decision_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Null when priority is INSUFFICIENT_DATA - there is no meaningful score to report"
    )
    factors: list[DecisionFactor] = Field(default_factory=list)
    rationale: str
    buying_intent: BuyingIntentAssessment
    contradictions: ContradictionReport
    why_now: WhyNowExplanation


class ChangeFactor(BaseModel):
    description: str
    evidence_needed: list[str] = Field(default_factory=list)


class DecisionChangeAnalysis(BaseModel):
    """'What would change our decision' - concrete, evidence-oriented next
    steps derived from gaps the rest of the pipeline already identified."""

    factors: list[ChangeFactor] = Field(default_factory=list)
    summary: str


class DecisionIntelligence(BaseModel):
    """Top-level Decision Intelligence bundle, attached to AnalysisExplanation."""

    recommendation: DecisionRecommendation
    change_analysis: DecisionChangeAnalysis
    evidence_confidence: list[EvidenceConfidenceScore] = Field(default_factory=list)
    source_reliability: list[SourceReliability] = Field(default_factory=list)
