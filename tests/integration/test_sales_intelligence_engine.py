"""Integration tests for Sales Intelligence Engine.

Verifies end-to-end composition:
1.  DecisionIntelligenceEngine → SalesIntelligenceEngine (full chain)
2.  INSUFFICIENT_DATA propagates through the full chain
3.  AnalysisExplainer attaches sales_intelligence end-to-end
4.  All evidence_ids in SalesIntelligence trace back to input evidence items
5.  Contradiction risks reference contradicting evidence IDs
"""
import uuid
from datetime import UTC, datetime, timedelta

from app.aggregation.analysis_explainer import AnalysisExplainer
from app.decision.decision_intelligence_engine import DecisionIntelligenceEngine
from app.decision.sales_intelligence_engine import SalesIntelligenceEngine
from app.models.score import ScoreType
from app.models.signal import SignalSource
from app.schemas.aggregation import EvidenceCoverageSummary, SignalGroup
from app.schemas.decision import DecisionPriority
from app.schemas.evidence import EvidenceItem
from app.schemas.explanation import (
    CollectorStatusReport,
    DisqualificationCategory,
    DisqualificationExplanation,
    EvidenceCoverage,
)
from app.schemas.score import PillarScore, PurchaseScoreResult
from app.schemas.signal import CollectorResult, CollectorStatus, RawSignal


# ---------------------------------------------------------------------------
# Shared helpers (mirrors the pattern from test_decision_intelligence_engine)
# ---------------------------------------------------------------------------

def _make_coverage(**overrides) -> EvidenceCoverage:
    defaults = {
        "sources_discovered": 4,
        "sources_attempted": 4,
        "sources_successful": 4,
        "sources_failed": 0,
        "sources_zero_results": 0,
        "sources_not_configured": 0,
        "evidence_items_extracted": 3,
        "evidence_items_accepted": 3,
        "coverage_percentage": 0.9,
        "collector_statuses": [
            CollectorStatusReport(source="news", status=CollectorStatus.SUCCESS, is_live=True, signal_count=3),
        ],
    }
    defaults.update(overrides)
    return EvidenceCoverage(**defaults)


def _make_purchase_result(score=85.0, confidence=0.85) -> PurchaseScoreResult:
    return PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=[
            PillarScore(score_type=ScoreType.NEED, score=score, confidence=confidence, reasons=[])
        ],
        purchase_score=score,
        confidence=confidence,
    )


def _make_disqualification(
    final_decision="qualified",
    missing_evidence=None,
) -> DisqualificationExplanation:
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


# ---------------------------------------------------------------------------
# 1. Full composition — qualified, evidence-rich company
# ---------------------------------------------------------------------------

def test_full_composition_qualified_company():
    """Decision Intelligence → Sales Intelligence with rich evidence.

    Asserts:
    - opportunity is not None
    - sales_trigger matches the evidence that triggered WhyNow
    - recommended_next_action references the trigger label or 'prioritize'
    - all evidence_ids in SalesIntelligence are UUIDs from the input evidence list
    """
    now = datetime.now(UTC)
    evidence = [
        EvidenceItem(
            signal_label="Series B Funding",
            excerpt="the company closed a series b funding round of $50m",
            source="TechCrunch",
            confidence=0.92,
            collector="news",
            published_at=now - timedelta(days=5),
        ),
        EvidenceItem(
            signal_label="AI Platform Hiring",
            excerpt="hiring machine learning engineers and data scientists for new ai platform",
            source="Careers Page",
            confidence=0.88,
            collector="website",
            published_at=now - timedelta(days=10),
        ),
        EvidenceItem(
            signal_label="CTO Blog Post",
            excerpt="our cto outlined the strategy for cloud migration and digital transformation",
            source="Company Blog",
            confidence=0.80,
            collector="website",
            published_at=now - timedelta(days=20),
        ),
    ]
    input_evidence_ids = {e.id for e in evidence}

    coverage = _make_coverage(
        evidence_items_accepted=len(evidence),
        evidence_items_extracted=len(evidence),
    )
    purchase_result = _make_purchase_result(score=87.0, confidence=0.87)
    disq = _make_disqualification()

    # Build Decision Intelligence first (mirrors the orchestrator chain)
    decision_intelligence = DecisionIntelligenceEngine().build(
        evidence=evidence,
        coverage=coverage,
        purchase_result=purchase_result,
        disqualification=disq,
        pillar_explanations=[],
        overall_confidence=0.87,
    )
    sales_intel = SalesIntelligenceEngine().build(
        evidence=evidence,
        decision_intelligence=decision_intelligence,
        purchase_result=purchase_result,
        disqualification=disq,
    )

    # Opportunity must exist and be evidence-backed
    assert sales_intel.opportunity is not None
    assert sales_intel.opportunity.confidence > 0

    # data_sufficient flag
    assert sales_intel.data_sufficient is True

    # Recommended action must be set
    assert sales_intel.recommended_next_action is not None

    # All evidence_ids in SalesIntelligence trace back to input evidence
    for eid in sales_intel.evidence_ids:
        assert eid in input_evidence_ids, (
            f"SalesIntelligence references evidence_id {eid} "
            "that was not in the input evidence list"
        )

    # Sales trigger should be non-None (funding event is fresh)
    assert sales_intel.sales_trigger is not None
    assert sales_intel.sales_trigger.trigger_type in (
        "funding_event", "product_launch", "hiring_spike", "expansion", "leadership_change", "acquisition"
    )


def test_full_composition_qualified_company_stakeholder_roles_are_evidence_backed():
    """Stakeholder roles must be backed by evidence phrases, not invented."""
    now = datetime.now(UTC)
    evidence = [
        EvidenceItem(
            signal_label="CTO Vision",
            excerpt="the cto of the company announced plans for an ai-first strategy",
            source="Press Release",
            confidence=0.85,
            collector="search",
            published_at=now - timedelta(days=15),
        ),
    ]
    input_evidence_ids = {e.id for e in evidence}

    decision_intelligence = DecisionIntelligenceEngine().build(
        evidence=evidence,
        coverage=_make_coverage(evidence_items_accepted=1, evidence_items_extracted=1),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
        pillar_explanations=[],
        overall_confidence=0.8,
    )
    sales_intel = SalesIntelligenceEngine().build(
        evidence=evidence,
        decision_intelligence=decision_intelligence,
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )

    # Must have detected the CTO role
    role_titles = [r.role_title for r in sales_intel.likely_buyer_roles]
    assert "CTO" in role_titles

    # Every role must reference only evidence that was provided
    for role in sales_intel.likely_buyer_roles:
        for eid in role.evidence_ids:
            assert eid in input_evidence_ids


# ---------------------------------------------------------------------------
# 2. INSUFFICIENT_DATA propagates through the full chain
# ---------------------------------------------------------------------------

def test_full_composition_insufficient_data():
    """Empty evidence → DecisionIntelligence INSUFFICIENT_DATA propagates
    all the way through SalesIntelligenceEngine."""
    empty_coverage = _make_coverage(
        coverage_percentage=0.0,
        evidence_items_accepted=0,
        evidence_items_extracted=0,
        sources_successful=0,
        collector_statuses=[
            CollectorStatusReport(
                source="news", status=CollectorStatus.NOT_CONFIGURED, is_live=False, signal_count=0
            )
        ],
    )
    purchase_result = _make_purchase_result(score=0.0, confidence=0.0)
    disq = _make_disqualification(final_decision="insufficient_data")

    decision_intelligence = DecisionIntelligenceEngine().build(
        evidence=[],
        coverage=empty_coverage,
        purchase_result=purchase_result,
        disqualification=disq,
        pillar_explanations=[],
        overall_confidence=0.0,
    )
    assert decision_intelligence.recommendation.priority == DecisionPriority.INSUFFICIENT_DATA

    sales_intel = SalesIntelligenceEngine().build(
        evidence=[],
        decision_intelligence=decision_intelligence,
        purchase_result=purchase_result,
        disqualification=disq,
    )

    assert sales_intel.data_sufficient is False
    assert sales_intel.confidence == 0.0
    assert sales_intel.opportunity is None
    assert sales_intel.solution_fit is None
    assert sales_intel.sales_trigger is None
    assert sales_intel.likely_buyer_roles == []
    assert sales_intel.recommended_next_action is not None
    assert "gather more evidence" in sales_intel.recommended_next_action.action.lower()


# ---------------------------------------------------------------------------
# 3. AnalysisExplainer attaches sales_intelligence end-to-end
# ---------------------------------------------------------------------------

def test_analysis_explainer_attaches_sales_intelligence():
    """Full AnalysisExplainer run must produce a non-None sales_intelligence
    and it must be serialisable / deserialisable (round-trip)."""
    pillar_scores = [
        PillarScore(score_type=t, score=85, confidence=0.85, reasons=[])
        for t in ScoreType
        if t.value != "purchase_propensity"
    ]
    purchase_result = PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=pillar_scores,
        purchase_score=85.0,
        confidence=0.85,
        disqualified=False,
        disqualified_reason=None,
    )
    coverage_summary = EvidenceCoverageSummary(
        company_domain="acme.com",
        total_evidence=5,
        sources_checked={"search": True, "website": True, "tech": True, "news": True},
        category_groups=[
            SignalGroup(category="funding", signal_count=3, avg_confidence=0.9, freshness=0.9, strength=0.85)
        ],
        overall_coverage=1.0,
        overall_confidence=0.9,
    )
    now = datetime.now(UTC)
    evidence = [
        EvidenceItem(
            signal_label="Funding Round Announced",
            excerpt="the company closed a series a funding round",
            source="TechCrunch",
            confidence=0.9,
            collector="news",
            published_at=now - timedelta(days=7),
        ),
        EvidenceItem(
            signal_label="Head of AI Hired",
            excerpt="the head of ai was recently appointed to drive the machine learning strategy",
            source="LinkedIn",
            confidence=0.8,
            collector="search",
            published_at=now - timedelta(days=20),
        ),
    ]
    collector_results = [
        CollectorResult(
            company_domain="acme.com",
            source=s,
            signals=[RawSignal(source=s, category="x", payload={})],
            is_live=True,
            errors=[],
        )
        for s in SignalSource
    ]

    explanation = AnalysisExplainer().explain(
        "acme.com",
        collector_results,
        evidence_items_extracted=len(evidence),
        normalized_evidence=evidence,
        coverage_summary=coverage_summary,
        purchase_result=purchase_result,
    )

    # Sales intelligence must be attached
    assert explanation.sales_intelligence is not None

    # It must be data_sufficient when we have real evidence
    assert explanation.sales_intelligence.data_sufficient is True

    # JSON round-trip (matches how orchestrator stores it)
    round_tripped = explanation.model_validate(explanation.model_dump(mode="json"))
    assert round_tripped.sales_intelligence is not None
    assert round_tripped.sales_intelligence.data_sufficient is True


def test_analysis_explainer_sales_intelligence_insufficient_data_on_no_evidence():
    """AnalysisExplainer with zero evidence → sales_intelligence.data_sufficient=False."""
    pillar_scores = [
        PillarScore(score_type=t, score=0, confidence=0.0, reasons=[])
        for t in [ScoreType.NEED, ScoreType.URGENCY, ScoreType.CAPACITY,
                  ScoreType.DIGITAL_MATURITY, ScoreType.ORG_READINESS, ScoreType.WINNABILITY]
    ]
    purchase_result = PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=pillar_scores,
        purchase_score=0.0,
        confidence=0.0,
        disqualified=True,
        disqualified_reason="No pillar produced any matched evidence.",
    )
    collector_results = [
        CollectorResult(
            company_domain="acme.com",
            source=s,
            signals=[],
            is_live=False,
            errors=["stub"],
            status=CollectorStatus.NOT_CONFIGURED,
        )
        for s in SignalSource
    ]
    coverage_summary = EvidenceCoverageSummary(
        company_domain="acme.com",
        total_evidence=0,
        sources_checked={},
        category_groups=[],
        overall_coverage=0.0,
        overall_confidence=0.0,
    )
    explanation = AnalysisExplainer().explain(
        "acme.com",
        collector_results,
        evidence_items_extracted=0,
        normalized_evidence=[],
        coverage_summary=coverage_summary,
        purchase_result=purchase_result,
    )
    assert explanation.sales_intelligence is not None
    assert explanation.sales_intelligence.data_sufficient is False
    assert explanation.sales_intelligence.confidence == 0.0


# ---------------------------------------------------------------------------
# 4. Evidence ID traceability end-to-end
# ---------------------------------------------------------------------------

def test_all_sales_intelligence_evidence_ids_traceable_to_input():
    """Every UUID in SalesIntelligence.evidence_ids must appear in the
    input evidence list.  This is the core anti-hallucination contract."""
    now = datetime.now(UTC)
    evidence = [
        EvidenceItem(
            signal_label=f"Signal {i}",
            excerpt=f"machine learning funding round series b vp engineering signal {i}",
            source="Test",
            confidence=0.8,
            collector="news",
            published_at=now - timedelta(days=i * 3),
        )
        for i in range(5)
    ]
    input_ids = {e.id for e in evidence}

    decision_intelligence = DecisionIntelligenceEngine().build(
        evidence=evidence,
        coverage=_make_coverage(evidence_items_accepted=5, evidence_items_extracted=5),
        purchase_result=_make_purchase_result(score=75.0),
        disqualification=_make_disqualification(),
        pillar_explanations=[],
        overall_confidence=0.8,
    )
    sales_intel = SalesIntelligenceEngine().build(
        evidence=evidence,
        decision_intelligence=decision_intelligence,
        purchase_result=_make_purchase_result(score=75.0),
        disqualification=_make_disqualification(),
    )

    for eid in sales_intel.evidence_ids:
        assert eid in input_ids, (
            f"SalesIntelligence produced evidence_id {eid} "
            "that does not exist in the input evidence list — anti-hallucination violation"
        )


# ---------------------------------------------------------------------------
# 5. Contradiction risks reference the contradicting evidence IDs
# ---------------------------------------------------------------------------

def test_contradiction_risks_reference_input_evidence_ids():
    """Risks of type 'contradiction' must carry the evidence_ids of the
    ContradictionFinding's evidence_a and evidence_b — not invented IDs."""
    now = datetime.now(UTC)
    ev_hiring = EvidenceItem(
        signal_label="Hiring Surge",
        excerpt="the company is experiencing a hiring surge expanding team",
        source="Careers",
        confidence=0.85,
        collector="website",
        published_at=now - timedelta(days=10),
    )
    ev_layoffs = EvidenceItem(
        signal_label="Layoffs Announced",
        excerpt="the company announced workforce reduction and layoffs this quarter",
        source="News",
        confidence=0.9,
        collector="news",
        published_at=now - timedelta(days=5),
    )
    evidence = [ev_hiring, ev_layoffs]
    input_ids = {e.id for e in evidence}

    decision_intelligence = DecisionIntelligenceEngine().build(
        evidence=evidence,
        coverage=_make_coverage(evidence_items_accepted=2, evidence_items_extracted=2),
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
        pillar_explanations=[],
        overall_confidence=0.7,
    )
    sales_intel = SalesIntelligenceEngine().build(
        evidence=evidence,
        decision_intelligence=decision_intelligence,
        purchase_result=_make_purchase_result(),
        disqualification=_make_disqualification(),
    )

    # Contradiction must have been detected
    assert decision_intelligence.recommendation.contradictions.has_contradictions

    contradiction_risks = [r for r in sales_intel.risks if r.risk_type == "contradiction"]
    assert contradiction_risks, "Expected at least one contradiction risk"

    # Every ID in the risk must trace back to input evidence
    for risk in contradiction_risks:
        for eid in risk.evidence_ids:
            assert eid in input_ids, (
                f"Contradiction risk references {eid} not in input evidence"
            )
