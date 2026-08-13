"""Schemas for the Sales Intelligence layer.

Every finding in this layer is derived exclusively from evidence that already
exists (EvidenceItem rows, the Decision Intelligence bundle, the purchase
score). Nothing here invents facts, individuals, or events.

Key invariants:
- Every opportunity, fit item, stakeholder role, trigger, risk, and next
  action carries an ``evidence_ids`` list so the claim can be traced back to
  the exact EvidenceItem(s) that produced it.
- ``data_sufficient=False`` means Decision Intelligence already reported
  INSUFFICIENT_DATA; the fields below carry explicit "insufficient data"
  explanations rather than silent empty lists so the consumer always knows
  why the field is empty.
- Missing evidence is reported as ``SalesRisk(risk_type='missing_evidence')``,
  never inferred as a negative signal.
"""
import uuid
from typing import Literal

from pydantic import BaseModel, Field


RiskType = Literal["contradiction", "missing_evidence", "existing_vendor", "other"]


class OpportunityItem(BaseModel):
    """The strongest business opportunity identified for this company.

    Backed by at least one EvidenceItem; the ``description`` is built
    deterministically from signal labels and excerpts - no invented prose.
    """

    description: str
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class SolutionFitItem(BaseModel):
    """Which solution / use-case best fits the company, and why.

    ``use_case`` is a named category drawn from a fixed taxonomy
    (e.g. 'AI/ML Platform Adoption', 'Talent & Capacity Expansion') -
    never invented from thin air. ``fit_reasoning`` is built from
    evidence labels; ``evidence_ids`` points to every item that
    contributed.
    """

    use_case: str
    fit_reasoning: str
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class StakeholderRole(BaseModel):
    """A *role title* (not a person) likely involved in the purchase decision.

    Derived from evidence phrases that mention a role title
    (e.g. 'CTO', 'VP Engineering', 'Head of AI').  The engine never
    produces a proper noun / individual name - only role titles that
    are directly supported by at least one evidence item.
    """

    role_title: str
    rationale: str
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class SalesTrigger(BaseModel):
    """The strongest reason to reach out *now*, drawn directly from the
    WhyNow engine's output - no recomputation.

    ``evidence_id`` traces back to the exact WhyNowTrigger.evidence_id
    so the salesperson can open the dossier on that item.
    """

    trigger_type: str
    label: str
    excerpt: str
    source: str
    evidence_id: uuid.UUID | None = None
    freshness_label: str
    narrative: str


class SalesRisk(BaseModel):
    """A single factor that could make the opportunity harder to close.

    risk_type taxonomy:
    - 'contradiction'    – directly from ContradictionReport.findings
    - 'missing_evidence' – from DisqualificationExplanation.missing_evidence
    - 'existing_vendor'  – evidence keyword matched a known competing vendor
    - 'other'            – catch-all for disqualification secondary reasons
    """

    description: str
    risk_type: RiskType
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class SalesAction(BaseModel):
    """One recommended next step, evidence-backed and priority-driven.

    The text is deterministic from the decision priority + whether a timing
    trigger was found - no LLM involved, so it can never contain an invented
    fact.
    """

    action: str
    rationale: str
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class SalesIntelligence(BaseModel):
    """Top-level Sales Intelligence bundle, attached to AnalysisExplanation.

    All nullable fields are None (not empty strings) when genuinely absent,
    so the consumer can distinguish "computed and empty" from "not computed."
    ``data_sufficient=False`` means the entire layer is operating on too
    little evidence to make any useful sales assertion.
    """

    opportunity: OpportunityItem | None = None
    solution_fit: SolutionFitItem | None = None
    likely_buyer_roles: list[StakeholderRole] = Field(default_factory=list)
    sales_trigger: SalesTrigger | None = None
    risks: list[SalesRisk] = Field(default_factory=list)
    recommended_next_action: SalesAction | None = None
    evidence_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Union of all evidence_ids referenced across every sub-field",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    data_sufficient: bool = Field(
        ...,
        description=(
            "False when Decision Intelligence flagged INSUFFICIENT_DATA - "
            "the fields above carry explicit explanations rather than silent nulls."
        ),
    )
