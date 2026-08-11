from app.decision.decision_change_analyzer import DecisionChangeAnalyzer
from app.models.score import ScoreType
from app.schemas.decision import (
    BuyingIntentAssessment,
    BuyingIntentLevel,
    ContradictionEvidenceRef,
    ContradictionFinding,
    ContradictionReport,
    ContradictionSeverity,
    DecisionPriority,
    DecisionRecommendation,
    WhyNowExplanation,
)
from app.schemas.explanation import CollectorStatusReport, EvidenceCoverage, PillarExplanation
from app.schemas.signal import CollectorStatus


def make_coverage(collector_statuses=None, sources_not_implemented=None):
    return EvidenceCoverage(
        sources_discovered=4,
        sources_attempted=4,
        sources_successful=0,
        sources_failed=0,
        sources_zero_results=0,
        sources_not_configured=4,
        evidence_items_extracted=0,
        evidence_items_accepted=0,
        coverage_percentage=0.0,
        collector_statuses=collector_statuses or [],
        sources_not_implemented=sources_not_implemented or [],
    )


def make_recommendation(priority, decision_score=0.5, has_contradictions=False, has_timing_trigger=True, buying_intent_level=BuyingIntentLevel.MODERATE):
    return DecisionRecommendation(
        priority=priority,
        decision_score=decision_score,
        factors=[],
        rationale="test",
        buying_intent=BuyingIntentAssessment(level=buying_intent_level, score=0.6, matched_signals=[], rationale="r"),
        contradictions=ContradictionReport(
            has_contradictions=has_contradictions,
            findings=[
                ContradictionFinding(
                    theme="hiring_trajectory",
                    severity=ContradictionSeverity.HIGH,
                    description="d",
                    evidence_a=ContradictionEvidenceRef(label="a", excerpt="a", source="s"),
                    evidence_b=ContradictionEvidenceRef(label="b", excerpt="b", source="s"),
                )
            ] if has_contradictions else [],
            summary="s",
        ),
        why_now=WhyNowExplanation(has_timing_trigger=has_timing_trigger, data_sufficient=True, triggers=[], narrative="n"),
    )


def make_pillar(score_type=ScoreType.NEED, score=20.0, missing=None):
    return PillarExplanation(
        score_type=score_type, score=score, confidence=0.5, missing_expected_signals=missing or []
    )


def test_insufficient_data_produces_data_gap_factors_from_failed_collectors():
    coverage = make_coverage(
        collector_statuses=[
            CollectorStatusReport(source="search", status=CollectorStatus.NOT_CONFIGURED, is_live=False, signal_count=0),
            CollectorStatusReport(source="github", status=CollectorStatus.SUCCESS, is_live=True, signal_count=3),
        ]
    )
    recommendation = make_recommendation(DecisionPriority.INSUFFICIENT_DATA, decision_score=None)
    analysis = DecisionChangeAnalyzer().analyze(recommendation, coverage, [])

    descriptions = " ".join(f.description for f in analysis.factors)
    assert "search" in descriptions
    assert "github" not in descriptions  # successful collector shouldn't be listed as a gap


def test_insufficient_data_lists_unimplemented_sources():
    coverage = make_coverage(sources_not_implemented=["Jobs", "Company Data"])
    recommendation = make_recommendation(DecisionPriority.INSUFFICIENT_DATA, decision_score=None)
    analysis = DecisionChangeAnalyzer().analyze(recommendation, coverage, [])

    descriptions = " ".join(f.description for f in analysis.factors)
    assert "Jobs" in descriptions
    assert "Company Data" in descriptions


def test_disqualified_low_priority_gets_fixed_summary_and_no_factors():
    coverage = make_coverage()
    recommendation = make_recommendation(DecisionPriority.LOW_PRIORITY, decision_score=0.0)
    analysis = DecisionChangeAnalyzer().analyze(recommendation, coverage, [])

    assert analysis.factors == []
    assert "disqualification" in analysis.summary.lower()


def test_qualified_low_priority_surfaces_weakest_pillar_gaps():
    coverage = make_coverage()
    recommendation = make_recommendation(DecisionPriority.LOW_PRIORITY, decision_score=0.3, has_timing_trigger=True)
    pillars = [
        make_pillar(ScoreType.NEED, score=10.0, missing=["hiring surge", "budget increase"]),
        make_pillar(ScoreType.CAPACITY, score=90.0, missing=["irrelevant signal"]),
    ]
    analysis = DecisionChangeAnalyzer().analyze(recommendation, coverage, pillars)

    descriptions = " ".join(f.description for f in analysis.factors)
    assert "hiring surge" in descriptions


def test_contradiction_factor_included_when_contradictions_present():
    coverage = make_coverage()
    recommendation = make_recommendation(DecisionPriority.MEDIUM_PRIORITY, has_contradictions=True)
    analysis = DecisionChangeAnalyzer().analyze(recommendation, coverage, [])

    assert any("contradictory" in f.description.lower() for f in analysis.factors)


def test_why_now_factor_included_when_no_timing_trigger():
    coverage = make_coverage()
    recommendation = make_recommendation(DecisionPriority.MEDIUM_PRIORITY, has_timing_trigger=False)
    analysis = DecisionChangeAnalyzer().analyze(recommendation, coverage, [])

    assert any("timing trigger" in f.description.lower() for f in analysis.factors)


def test_buying_intent_factor_included_when_weak_or_none():
    coverage = make_coverage()
    recommendation = make_recommendation(DecisionPriority.MEDIUM_PRIORITY, buying_intent_level=BuyingIntentLevel.WEAK)
    analysis = DecisionChangeAnalyzer().analyze(recommendation, coverage, [])

    assert any("procurement" in f.description.lower() for f in analysis.factors)


def test_factors_are_capped_at_six():
    coverage = make_coverage()
    recommendation = make_recommendation(DecisionPriority.LOW_PRIORITY, decision_score=0.3, has_contradictions=True, has_timing_trigger=False, buying_intent_level=BuyingIntentLevel.NONE)
    pillars = [
        make_pillar(ScoreType.NEED, score=10.0, missing=["a", "b"]),
        make_pillar(ScoreType.URGENCY, score=15.0, missing=["c", "d"]),
        make_pillar(ScoreType.CAPACITY, score=20.0, missing=["e", "f"]),
    ]
    analysis = DecisionChangeAnalyzer().analyze(recommendation, coverage, pillars)

    assert len(analysis.factors) <= 6
