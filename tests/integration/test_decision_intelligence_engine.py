"""Integration coverage for Decision Intelligence: verifies the composition
layer (DecisionIntelligenceEngine) wires its sub-engines together correctly,
and that AnalysisExplainer attaches the result end-to-end for both a
qualified, evidence-rich company and a data-starved one."""
from datetime import UTC, datetime, timedelta

from app.aggregation.analysis_explainer import AnalysisExplainer
from app.decision.decision_intelligence_engine import DecisionIntelligenceEngine
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


def make_coverage(**overrides):
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
            CollectorStatusReport(source="github", status=CollectorStatus.SUCCESS, is_live=True, signal_count=3),
        ],
    }
    defaults.update(overrides)
    return EvidenceCoverage(**defaults)


def make_purchase_result(score=85.0, confidence=0.85):
    return PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=[PillarScore(score_type=ScoreType.NEED, score=score, confidence=confidence, reasons=[])],
        purchase_score=score,
        confidence=confidence,
    )


def make_disqualification(final_decision="qualified"):
    return DisqualificationExplanation(
        final_decision=final_decision,
        category=DisqualificationCategory.NOT_DISQUALIFIED
        if final_decision == "qualified"
        else DisqualificationCategory.COLLECTION_FAILURE,
        primary_reason="test",
        confidence=0.8,
        recommended_next_action="proceed",
    )


def test_decision_intelligence_engine_produces_a_full_bundle_for_rich_evidence():
    now = datetime.now(UTC)
    evidence = [
        EvidenceItem(
            signal_label="RFP Issued",
            excerpt="the company issued a request for proposal for automation vendors",
            source="News",
            confidence=0.9,
            collector="news",
            published_at=now - timedelta(days=3),
        ),
        EvidenceItem(
            signal_label="Funding Round",
            excerpt="the company closed a series b funding round",
            source="TechCrunch",
            confidence=0.85,
            collector="news",
            published_at=now - timedelta(days=10),
        ),
    ]
    bundle = DecisionIntelligenceEngine().build(
        evidence=evidence,
        coverage=make_coverage(),
        purchase_result=make_purchase_result(),
        disqualification=make_disqualification(),
        pillar_explanations=[],
        overall_confidence=0.85,
    )

    assert bundle.recommendation.priority in (
        DecisionPriority.HIGH_PRIORITY,
        DecisionPriority.MEDIUM_PRIORITY,
        DecisionPriority.LOW_PRIORITY,
    )
    assert bundle.recommendation.buying_intent.level.value == "strong"
    assert bundle.recommendation.why_now.has_timing_trigger is True
    assert len(bundle.evidence_confidence) == 2
    assert len(bundle.source_reliability) == 1
    assert bundle.source_reliability[0].collector == "news"


def test_decision_intelligence_engine_respects_insufficient_data_end_to_end():
    bundle = DecisionIntelligenceEngine().build(
        evidence=[],
        coverage=make_coverage(
            coverage_percentage=0.0,
            evidence_items_accepted=0,
            sources_successful=0,
            collector_statuses=[
                CollectorStatusReport(source="github", status=CollectorStatus.NOT_CONFIGURED, is_live=False, signal_count=0),
            ],
        ),
        purchase_result=make_purchase_result(score=0.0, confidence=0.0),
        disqualification=make_disqualification(final_decision="insufficient_data"),
        pillar_explanations=[],
        overall_confidence=0.0,
    )

    assert bundle.recommendation.priority == DecisionPriority.INSUFFICIENT_DATA
    assert bundle.recommendation.decision_score is None
    # Buying intent must not claim "none" when we never had a real look.
    assert bundle.recommendation.buying_intent.level.value == "insufficient_data"
    assert bundle.change_analysis.factors  # should surface data-gap next-steps


def test_evidence_confidence_and_source_reliability_are_consistent_with_each_other():
    """Every collector referenced in per-item evidence_confidence scores
    should also appear in the aggregated source_reliability breakdown -
    the two views must never disagree about which sources were seen."""
    evidence = [
        EvidenceItem(signal_label="x", excerpt="x", source="s", confidence=0.7, collector="github"),
        EvidenceItem(signal_label="y", excerpt="y", source="s", confidence=0.6, collector="search"),
    ]
    bundle = DecisionIntelligenceEngine().build(
        evidence=evidence,
        coverage=make_coverage(),
        purchase_result=make_purchase_result(),
        disqualification=make_disqualification(),
        pillar_explanations=[],
        overall_confidence=0.7,
    )

    confidence_collectors = {s.collector for s in bundle.evidence_confidence}
    reliability_collectors = {s.collector for s in bundle.source_reliability}
    assert confidence_collectors == reliability_collectors


def test_analysis_explainer_attaches_decision_intelligence_for_qualified_company():
    pillar_scores = [
        PillarScore(score_type=t, score=90, confidence=0.9, reasons=[])
        for t in ScoreType
        if t.value != "purchase_propensity"
    ]
    purchase_result = PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=pillar_scores,
        purchase_score=90.0,
        confidence=0.9,
        disqualified=False,
        disqualified_reason=None,
    )
    coverage_summary = EvidenceCoverageSummary(
        company_domain="acme.com",
        total_evidence=10,
        sources_checked={"search": True, "website": True, "tech": True, "news": True},
        category_groups=[SignalGroup(category="hiring", signal_count=5, avg_confidence=0.9, freshness=0.9, strength=0.8)],
        overall_coverage=1.0,
        overall_confidence=0.9,
    )
    evidence = [
        EvidenceItem(
            signal_label="Hiring AI Engineers", excerpt="we are hiring", source="Careers Page", confidence=0.9, collector="website"
        )
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
        evidence_items_extracted=1,
        normalized_evidence=evidence,
        coverage_summary=coverage_summary,
        purchase_result=purchase_result,
    )

    assert explanation.decision_intelligence is not None
    assert explanation.decision_intelligence.recommendation.priority != DecisionPriority.INSUFFICIENT_DATA
    # Round-trips cleanly through the same JSON-serialization path the DB uses.
    assert explanation.model_validate(explanation.model_dump()) is not None


def test_analysis_explainer_forces_insufficient_data_priority_when_disqualified_from_poor_coverage():
    purchase_result = PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=[
            PillarScore(score_type=t, score=0, confidence=0, reasons=[])
            for t in [
                ScoreType.NEED,
                ScoreType.URGENCY,
                ScoreType.CAPACITY,
                ScoreType.DIGITAL_MATURITY,
                ScoreType.ORG_READINESS,
                ScoreType.WINNABILITY,
            ]
        ],
        purchase_score=0.0,
        confidence=0.0,
        disqualified=True,
        disqualified_reason="No pillar produced any matched evidence.",
    )
    collector_results = [
        CollectorResult(
            company_domain="acme.com", source=s, signals=[], is_live=False, errors=["stub"], status=CollectorStatus.NOT_CONFIGURED
        )
        for s in SignalSource
    ]
    coverage_summary = EvidenceCoverageSummary(
        company_domain="acme.com", total_evidence=0, sources_checked={}, category_groups=[], overall_coverage=0.0, overall_confidence=0.0
    )

    explanation = AnalysisExplainer().explain(
        "acme.com",
        collector_results,
        evidence_items_extracted=0,
        normalized_evidence=[],
        coverage_summary=coverage_summary,
        purchase_result=purchase_result,
    )

    assert explanation.decision_intelligence.recommendation.priority == DecisionPriority.INSUFFICIENT_DATA
    assert explanation.decision_intelligence.recommendation.decision_score is None
    assert explanation.decision_intelligence.recommendation.buying_intent.level.value == "insufficient_data"
