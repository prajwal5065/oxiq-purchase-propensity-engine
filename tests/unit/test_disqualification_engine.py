from app.aggregation.disqualification_engine import DisqualificationEngine
from app.models.score import ScoreType
from app.schemas.explanation import (
    CollectorStatusReport,
    DisqualificationCategory,
    EvidenceCoverage,
    PillarExplanation,
)
from app.schemas.score import PurchaseScoreResult
from app.schemas.signal import CollectorStatus


def purchase_result(disqualified=True, reason="No pillar produced any matched evidence.", confidence=0.0):
    return PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=[],
        purchase_score=0.0,
        confidence=confidence,
        evidence_summary=[],
        disqualified=disqualified,
        disqualified_reason=reason if disqualified else None,
    )


def coverage(
    sources_discovered=4,
    sources_successful=0,
    sources_failed=0,
    sources_zero_results=0,
    sources_not_configured=0,
    evidence_items_accepted=0,
    coverage_percentage=0.0,
    statuses=None,
):
    return EvidenceCoverage(
        sources_discovered=sources_discovered,
        sources_attempted=sources_discovered,
        sources_successful=sources_successful,
        sources_failed=sources_failed,
        sources_zero_results=sources_zero_results,
        sources_not_configured=sources_not_configured,
        evidence_items_extracted=evidence_items_accepted,
        evidence_items_accepted=evidence_items_accepted,
        coverage_percentage=coverage_percentage,
        collector_statuses=statuses or [],
    )


def test_not_disqualified_returns_qualified_decision():
    result = purchase_result(disqualified=False, confidence=0.8)
    explanation = DisqualificationEngine().explain(result, coverage(), pillar_explanations=[])
    assert explanation.final_decision == "qualified"
    assert explanation.category == DisqualificationCategory.NOT_DISQUALIFIED


def test_all_collectors_failed_is_collection_failure_not_negative_evidence():
    result = purchase_result()
    cov = coverage(
        sources_successful=0,
        sources_failed=4,
        statuses=[
            CollectorStatusReport(source="search", status=CollectorStatus.ERROR, is_live=True, signal_count=0, errors=["boom"])
        ],
    )
    explanation = DisqualificationEngine().explain(result, cov, pillar_explanations=[])

    assert explanation.category == DisqualificationCategory.COLLECTION_FAILURE
    assert explanation.final_decision == "insufficient_data"
    assert explanation.final_decision != "disqualified"


def test_all_stub_mode_is_source_unavailable_not_negative_evidence():
    result = purchase_result()
    cov = coverage(sources_successful=0, sources_not_configured=4)
    explanation = DisqualificationEngine().explain(result, cov, pillar_explanations=[])

    assert explanation.category == DisqualificationCategory.SOURCE_UNAVAILABLE
    assert explanation.final_decision == "insufficient_data"


def test_low_coverage_with_some_evidence_is_insufficient_not_negative():
    result = purchase_result()
    cov = coverage(
        sources_successful=1,
        sources_zero_results=3,
        evidence_items_accepted=1,
        coverage_percentage=0.25,
    )
    explanation = DisqualificationEngine().explain(result, cov, pillar_explanations=[])

    assert explanation.category == DisqualificationCategory.INSUFFICIENT_EVIDENCE
    assert explanation.final_decision == "insufficient_data"


def test_good_coverage_but_still_disqualified_is_genuine_negative_evidence():
    result = purchase_result(reason="Capacity too low to support a purchase.")
    cov = coverage(
        sources_successful=4,
        evidence_items_accepted=10,
        coverage_percentage=1.0,
    )
    explanation = DisqualificationEngine().explain(result, cov, pillar_explanations=[])

    assert explanation.category == DisqualificationCategory.GENUINE_NEGATIVE_EVIDENCE
    assert explanation.final_decision == "disqualified"


def test_genuine_negative_evidence_never_reported_when_coverage_was_poor():
    """The core guardrail: no matter how the rule engine phrased its reason,
    if we didn't actually have enough evidence to look, that must never come
    back as 'disqualified' (a business conclusion)."""
    result = purchase_result(reason="No pillar produced any matched evidence.")
    cov = coverage(sources_successful=0, sources_not_configured=4)
    explanation = DisqualificationEngine().explain(result, cov, pillar_explanations=[])

    assert explanation.category != DisqualificationCategory.GENUINE_NEGATIVE_EVIDENCE
    assert explanation.final_decision != "disqualified"


def test_missing_evidence_lists_non_successful_sources():
    result = purchase_result()
    cov = coverage(
        sources_successful=0,
        sources_not_configured=1,
        statuses=[
            CollectorStatusReport(source="search", status=CollectorStatus.NOT_CONFIGURED, is_live=False, signal_count=0, errors=[])
        ],
    )
    explanation = DisqualificationEngine().explain(result, cov, pillar_explanations=[])
    assert any("search" in m for m in explanation.missing_evidence)


def test_qualified_supporting_evidence_pulled_from_pillar_explanations():
    result = purchase_result(disqualified=False, confidence=0.8)
    from app.schemas.explanation import ScoreContribution

    pillar = PillarExplanation(
        score_type=ScoreType.NEED,
        score=80,
        confidence=0.8,
        positive_evidence=[
            ScoreContribution(label="Hiring AI Engineers", excerpt="x", source="Careers Page", points=40, direction="positive")
        ],
    )
    explanation = DisqualificationEngine().explain(result, coverage(), pillar_explanations=[pillar])
    assert "Hiring AI Engineers" in explanation.supporting_evidence
