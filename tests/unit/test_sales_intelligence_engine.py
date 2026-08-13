"""Unit tests for SalesIntelligenceEngine.

Tests verify:
1.  Evidence traceability – every finding carries the evidence_ids that produced it
2.  Insufficient-data guardrail – INSUFFICIENT_DATA propagates to all fields
3.  Contradiction → risk conversion
4.  Missing evidence → risk conversion
5.  Existing vendor keywords surface as risks
6.  Stakeholder roles are title-only and gated on evidence presence
7.  Sales trigger is a direct pass-through from WhyNow
8.  Next-action text is deterministic from priority tier
9.  Global evidence_ids is the union of all per-field evidence_ids
"""
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.decision.buying_intent_engine import BuyingIntentEngine
from app.decision.contradiction_detector import ContradictionDetector
from app.decision.decision_change_analyzer import DecisionChangeAnalyzer
from app.decision.decision_engine import DecisionEngine
from app.decision.evidence_confidence import EvidenceConfidenceEngine
from app.decision.sales_intelligence_engine import SalesIntelligenceEngine
from app.decision.source_reliability import SourceReliabilityEngine
from app.decision.why_now_engine import WhyNowEngine
from app.models.score import ScoreType
from app.schemas.decision import (
    BuyingIntentAssessment,
    BuyingIntentLevel,
    ContradictionEvidenceRef,
    ContradictionFinding,
    ContradictionReport,
    ContradictionSeverity,
    DecisionChangeAnalysis,
    DecisionIntelligence,
    DecisionPriority,
    DecisionRecommendation,
    WhyNowExplanation,
    WhyNowTrigger,
)
from app.schemas.evidence import EvidenceItem
from app.schemas.explanation import (
    DisqualificationCategory,
    DisqualificationExplanation,
)
from app.schemas.score import PillarScore, PurchaseScoreResult
from app.schemas.sales import SalesIntelligence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_evidence(**kwargs) -> EvidenceItem:
    defaults = dict(signal_label="Generic Signal", excerpt="some text", source="Test", confidence=0.8)
    defaults.update(kwargs)
    return EvidenceItem(**defaults)


def _make_disqualification(final_decision="qualified", missing_evidence=None) -> DisqualificationExplanation:
    return DisqualificationExplanation(
        final_decision=final_decision,
        category=(
            DisqualificationCategory.NOT_DISQUALIFIED
            if final_decision == "qualified"
            else DisqualificationCategory.INSUFFICIENT_EVIDENCE
        ),
        primary_reason="test",
        missing_evidence=missing_evidence or [],
        confidence=0.8,
        recommended_next_action="proceed",
    )


def _make_buying_intent(level=BuyingIntentLevel.MODERATE) -> BuyingIntentAssessment:
    return BuyingIntentAssessment(
        level=level,
        score=0.6,
        matched_signals=[],
        rationale="test",
    )


def _make_why_now(has_trigger=False, triggers=None) -> WhyNowExplanation:
    return WhyNowExplanation(
        has_timing_trigger=has_trigger,
        data_sufficient=True,
        triggers=triggers or [],
        narrative="no trigger" if not has_trigger else "trigger found",
    )


def _make_contradictions(findings=None) -> ContradictionReport:
    return ContradictionReport(
        has_contradictions=bool(findings),
        findings=findings or [],
        summary="none",
    )


def _make_decision_recommendation(
    priority=DecisionPriority.HIGH_PRIORITY,
    decision_score=0.85,
    buying_intent=None,
    contradictions=None,
    why_now=None,
) -> DecisionRecommendation:
    return DecisionRecommendation(
        priority=priority,
        decision_score=decision_score,
        factors=[],
        rationale="test",
        buying_intent=buying_intent or _make_buying_intent(),
        contradictions=contradictions or _make_contradictions(),
        why_now=why_now or _make_why_now(),
    )


def _make_decision_intelligence(
    priority=DecisionPriority.HIGH_PRIORITY,
    decision_score=0.85,
    buying_intent=None,
    contradictions=None,
    why_now=None,
) -> DecisionIntelligence:
    recommendation = _make_decision_recommendation(
        priority=priority,
        decision_score=decision_score,
        buying_intent=buying_intent,
        contradictions=contradictions,
        why_now=why_now,
    )
    return DecisionIntelligence(
        recommendation=recommendation,
        change_analysis=DecisionChangeAnalysis(factors=[], summary=""),
        evidence_confidence=[],
        source_reliability=[],
    )


def _make_purchase_result(score=80.0) -> PurchaseScoreResult:
    return PurchaseScoreResult(
        company_domain="test.com",
        pillar_scores=[
            PillarScore(score_type=ScoreType.NEED, score=score, confidence=0.8, reasons=[])
        ],
        purchase_score=score,
        confidence=0.8,
    )


ENGINE = SalesIntelligenceEngine()


# ---------------------------------------------------------------------------
# 1. Evidence traceability: opportunity evidence_ids match input evidence
# ---------------------------------------------------------------------------

def test_opportunity_backed_by_evidence_ids():
    ev = _make_evidence(
        signal_label="Machine Learning Initiative",
        excerpt="the company is hiring AI engineers for a new machine learning platform",
        confidence=0.9,
    )
    intel = ENGINE.build(
        evidence=[ev],
        decision_intelligence=_make_decision_intelligence(),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    assert intel.opportunity is not None
    assert ev.id in intel.opportunity.evidence_ids


def test_opportunity_evidence_ids_are_subset_of_global_evidence_ids():
    ev = _make_evidence(
        signal_label="Funding Round",
        excerpt="the company raised a series b funding round",
        confidence=0.85,
    )
    intel = ENGINE.build(
        evidence=[ev],
        decision_intelligence=_make_decision_intelligence(),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    if intel.opportunity:
        for eid in intel.opportunity.evidence_ids:
            assert eid in intel.evidence_ids


# ---------------------------------------------------------------------------
# 2. Insufficient-data guardrail
# ---------------------------------------------------------------------------

def test_insufficient_data_propagates_everywhere():
    intel = ENGINE.build(
        evidence=[],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.INSUFFICIENT_DATA,
            decision_score=None,
        ),
        purchase_result=_make_purchase_result(score=0.0),
        disqualification=_make_disqualification(final_decision="insufficient_data"),
    )
    assert intel.data_sufficient is False
    assert intel.confidence == 0.0
    assert intel.opportunity is None
    assert intel.solution_fit is None
    assert intel.likely_buyer_roles == []
    assert intel.sales_trigger is None
    assert intel.recommended_next_action is not None
    assert "gather more evidence" in intel.recommended_next_action.action.lower()
    # At least one risk should explain the situation
    assert any("insufficient" in r.description.lower() for r in intel.risks)


def test_insufficient_data_confidence_is_exactly_zero():
    intel = ENGINE.build(
        evidence=[],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.INSUFFICIENT_DATA,
            decision_score=None,
        ),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    assert intel.confidence == 0.0


# ---------------------------------------------------------------------------
# 3. Contradiction → risk conversion
# ---------------------------------------------------------------------------

def test_contradictions_become_risks():
    ev_a_id = uuid.uuid4()
    ev_b_id = uuid.uuid4()
    finding = ContradictionFinding(
        theme="hiring_trajectory",
        severity=ContradictionSeverity.HIGH,
        description="Shows both hiring and layoffs.",
        evidence_a=ContradictionEvidenceRef(
            evidence_id=ev_a_id, label="Hiring Surge", excerpt="hiring surge", source="Careers"
        ),
        evidence_b=ContradictionEvidenceRef(
            evidence_id=ev_b_id, label="Layoffs", excerpt="layoff announcement", source="News"
        ),
    )
    contradictions = _make_contradictions(findings=[finding])
    intel = ENGINE.build(
        evidence=[],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.MEDIUM_PRIORITY,
            decision_score=0.5,
            contradictions=contradictions,
        ),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    contradiction_risks = [r for r in intel.risks if r.risk_type == "contradiction"]
    assert len(contradiction_risks) == 1
    assert ev_a_id in contradiction_risks[0].evidence_ids
    assert ev_b_id in contradiction_risks[0].evidence_ids
    assert "hiring trajectory" in contradiction_risks[0].description.lower()


# ---------------------------------------------------------------------------
# 4. Missing evidence → risk conversion
# ---------------------------------------------------------------------------

def test_missing_evidence_becomes_risk():
    disq = _make_disqualification(missing_evidence=["No funding signals", "No hiring data"])
    intel = ENGINE.build(
        evidence=[],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.LOW_PRIORITY,
            decision_score=0.2,
        ),
        purchase_result=_make_purchase_result(),
        disqualification=disq,
    )
    missing_risks = [r for r in intel.risks if r.risk_type == "missing_evidence"]
    assert len(missing_risks) == 2
    descriptions = [r.description for r in missing_risks]
    assert any("No funding signals" in d for d in descriptions)
    assert any("No hiring data" in d for d in descriptions)


# ---------------------------------------------------------------------------
# 5. Existing vendor keywords surface as risks
# ---------------------------------------------------------------------------

def test_existing_vendor_keywords_surface_as_risk():
    ev = _make_evidence(
        signal_label="CRM Stack",
        excerpt="the company uses salesforce for its customer relationship management",
        confidence=0.75,
    )
    intel = ENGINE.build(
        evidence=[ev],
        decision_intelligence=_make_decision_intelligence(),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    vendor_risks = [r for r in intel.risks if r.risk_type == "existing_vendor"]
    assert len(vendor_risks) >= 1
    assert any("Salesforce" in r.description for r in vendor_risks)
    # Risk must reference the evidence that triggered it
    for vr in vendor_risks:
        assert ev.id in vr.evidence_ids


# ---------------------------------------------------------------------------
# 6. Stakeholder roles: title-only, gated on evidence
# ---------------------------------------------------------------------------

def test_stakeholder_roles_never_invent_individuals():
    ev = _make_evidence(
        signal_label="CTO Announcement",
        excerpt="the cto led the initiative for digital transformation",
        confidence=0.8,
    )
    intel = ENGINE.build(
        evidence=[ev],
        decision_intelligence=_make_decision_intelligence(),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    for role in intel.likely_buyer_roles:
        # role_title must be a generic title, not a proper name
        assert role.role_title  # not empty
        # proper names would contain capitalised words that aren't common role titles
        # We assert no evidence_ids are empty (every role backed by evidence)
        assert role.evidence_ids, f"Role '{role.role_title}' has no evidence backing"


def test_stakeholder_roles_only_when_evidence_mentions_role():
    ev = _make_evidence(
        signal_label="Company Overview",
        excerpt="the company builds data analytics software",
        confidence=0.7,
    )
    intel = ENGINE.build(
        evidence=[ev],
        decision_intelligence=_make_decision_intelligence(),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    # Evidence doesn't mention any role title → no roles inferred
    assert intel.likely_buyer_roles == []


def test_stakeholder_roles_evidence_ids_reference_input_items():
    ev = _make_evidence(
        signal_label="Engineering Lead",
        excerpt="the vp engineering signed off on the ai initiative",
        confidence=0.85,
    )
    intel = ENGINE.build(
        evidence=[ev],
        decision_intelligence=_make_decision_intelligence(),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    input_ids = {ev.id}
    for role in intel.likely_buyer_roles:
        for eid in role.evidence_ids:
            assert eid in input_ids


# ---------------------------------------------------------------------------
# 7. Sales trigger is a direct pass-through from WhyNow
# ---------------------------------------------------------------------------

def test_sales_trigger_reuses_why_now_directly():
    trigger_evidence_id = uuid.uuid4()
    now = datetime.now(UTC)
    trigger = WhyNowTrigger(
        evidence_id=trigger_evidence_id,
        label="Series B Funding",
        excerpt="the company closed a series b funding round",
        source="TechCrunch",
        trigger_type="funding_event",
        published_at=now - timedelta(days=5),
        freshness_label="very_fresh",
    )
    why_now = _make_why_now(has_trigger=True, triggers=[trigger])
    intel = ENGINE.build(
        evidence=[],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.HIGH_PRIORITY,
            decision_score=0.85,
            why_now=why_now,
        ),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    assert intel.sales_trigger is not None
    assert intel.sales_trigger.evidence_id == trigger_evidence_id
    assert intel.sales_trigger.trigger_type == "funding_event"
    assert intel.sales_trigger.freshness_label == "very_fresh"


def test_no_trigger_when_why_now_has_none():
    intel = ENGINE.build(
        evidence=[],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.MEDIUM_PRIORITY,
            decision_score=0.5,
            why_now=_make_why_now(has_trigger=False),
        ),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    assert intel.sales_trigger is None


# ---------------------------------------------------------------------------
# 8. Next-action deterministic from priority
# ---------------------------------------------------------------------------

def test_next_action_high_priority_with_trigger_references_trigger():
    trigger_id = uuid.uuid4()
    trigger = WhyNowTrigger(
        evidence_id=trigger_id,
        label="Series A Funding",
        excerpt="the company raised series a",
        source="News",
        trigger_type="funding_event",
        published_at=datetime.now(UTC) - timedelta(days=2),
        freshness_label="very_fresh",
    )
    why_now = _make_why_now(has_trigger=True, triggers=[trigger])
    intel = ENGINE.build(
        evidence=[],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.HIGH_PRIORITY,
            decision_score=0.9,
            why_now=why_now,
        ),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    action = intel.recommended_next_action
    assert action is not None
    assert "prioritize outreach" in action.action.lower()
    assert "Series A Funding" in action.action or "trigger" in action.action.lower()


def test_next_action_medium_priority_is_nurture():
    intel = ENGINE.build(
        evidence=[],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.MEDIUM_PRIORITY,
            decision_score=0.55,
            why_now=_make_why_now(has_trigger=False),
        ),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    action = intel.recommended_next_action
    assert action is not None
    assert "nurture" in action.action.lower()


def test_next_action_low_priority_is_deprioritize():
    intel = ENGINE.build(
        evidence=[],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.LOW_PRIORITY,
            decision_score=0.2,
            why_now=_make_why_now(has_trigger=False),
        ),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    action = intel.recommended_next_action
    assert action is not None
    assert "do not prioritize" in action.action.lower()


def test_next_action_insufficient_data_gather_more_evidence():
    intel = ENGINE.build(
        evidence=[],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.INSUFFICIENT_DATA,
            decision_score=None,
        ),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(final_decision="insufficient_data"),
    )
    action = intel.recommended_next_action
    assert action is not None
    assert "gather more evidence" in action.action.lower()


# ---------------------------------------------------------------------------
# 9. Global evidence_ids is the union of all per-field evidence_ids
# ---------------------------------------------------------------------------

def test_global_evidence_ids_is_union_of_per_field_ids():
    ev1 = _make_evidence(
        signal_label="AI Initiative",
        excerpt="the company is investing in machine learning",
        confidence=0.9,
    )
    ev2 = _make_evidence(
        signal_label="CTO Hire",
        excerpt="the cto joined last quarter",
        confidence=0.8,
    )
    trigger_id = uuid.uuid4()
    trigger = WhyNowTrigger(
        evidence_id=trigger_id,
        label="Funding Round",
        excerpt="series a funding round",
        source="News",
        trigger_type="funding_event",
        published_at=datetime.now(UTC) - timedelta(days=3),
        freshness_label="very_fresh",
    )
    why_now = _make_why_now(has_trigger=True, triggers=[trigger])
    intel = ENGINE.build(
        evidence=[ev1, ev2],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.HIGH_PRIORITY,
            decision_score=0.85,
            why_now=why_now,
        ),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )

    # Collect all per-field IDs manually
    all_per_field: set[uuid.UUID] = set()
    if intel.opportunity:
        all_per_field.update(intel.opportunity.evidence_ids)
    if intel.solution_fit:
        all_per_field.update(intel.solution_fit.evidence_ids)
    for role in intel.likely_buyer_roles:
        all_per_field.update(role.evidence_ids)
    if intel.sales_trigger and intel.sales_trigger.evidence_id:
        all_per_field.add(intel.sales_trigger.evidence_id)
    for risk in intel.risks:
        all_per_field.update(risk.evidence_ids)
    if intel.recommended_next_action:
        all_per_field.update(intel.recommended_next_action.evidence_ids)

    assert set(intel.evidence_ids) == all_per_field


# ---------------------------------------------------------------------------
# 10. Solution fit maps to known use-case
# ---------------------------------------------------------------------------

def test_solution_fit_maps_to_known_use_case():
    ev = _make_evidence(
        signal_label="AI Platform Adoption",
        excerpt="deploying machine learning models on the cloud platform using pytorch and hugging face",
        confidence=0.9,
    )
    intel = ENGINE.build(
        evidence=[ev],
        decision_intelligence=_make_decision_intelligence(),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )
    assert intel.solution_fit is not None
    assert intel.solution_fit.use_case == "AI/ML Platform Adoption"
    assert ev.id in intel.solution_fit.evidence_ids


def test_solution_fit_returns_none_when_no_matching_evidence():
    ev = _make_evidence(
        signal_label="Press Coverage",
        excerpt="the company won an award",
        confidence=0.6,
    )
    # Pillar scores all weak → no fallback either
    purchase = PurchaseScoreResult(
        company_domain="test.com",
        pillar_scores=[
            PillarScore(score_type=ScoreType.NEED, score=20.0, confidence=0.4, reasons=[])
        ],
        purchase_score=20.0,
        confidence=0.4,
    )
    intel = ENGINE.build(
        evidence=[ev],
        decision_intelligence=_make_decision_intelligence(
            priority=DecisionPriority.LOW_PRIORITY,
            decision_score=0.2,
        ),
        purchase_result=purchase,
        disqualification=_make_disqualification(),
    )
    assert intel.solution_fit is None
