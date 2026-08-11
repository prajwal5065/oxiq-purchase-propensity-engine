from app.decision.decision_engine import DecisionEngine
from app.models.score import ScoreType
from app.schemas.decision import (
    BuyingIntentAssessment,
    BuyingIntentLevel,
    ContradictionEvidenceRef,
    ContradictionFinding,
    ContradictionReport,
    ContradictionSeverity,
    DecisionPriority,
    WhyNowExplanation,
)
from app.schemas.explanation import DisqualificationCategory, DisqualificationExplanation
from app.schemas.score import PillarScore, PurchaseScoreResult


def make_purchase_result(score=80.0, confidence=0.8):
    return PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=[PillarScore(score_type=ScoreType.NEED, score=score, confidence=confidence, reasons=[])],
        purchase_score=score,
        confidence=confidence,
    )


def make_disqualification(final_decision="qualified", category=DisqualificationCategory.NOT_DISQUALIFIED):
    return DisqualificationExplanation(
        final_decision=final_decision,
        category=category,
        primary_reason="test reason",
        confidence=0.8,
        recommended_next_action="proceed",
    )


def make_buying_intent(level=BuyingIntentLevel.MODERATE, score=0.6):
    return BuyingIntentAssessment(level=level, score=score, matched_signals=[], rationale="test")


def no_contradictions():
    return ContradictionReport(has_contradictions=False, findings=[], summary="none")


def no_why_now():
    return WhyNowExplanation(has_timing_trigger=False, data_sufficient=True, triggers=[], narrative="none")


def test_insufficient_data_guardrail_overrides_all_computed_factors():
    disqualification = make_disqualification(
        final_decision="insufficient_data", category=DisqualificationCategory.COLLECTION_FAILURE
    )
    result = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=95.0, confidence=0.95),
        disqualification=disqualification,
        buying_intent=make_buying_intent(level=BuyingIntentLevel.STRONG, score=1.0),
        contradictions=no_contradictions(),
        why_now=no_why_now(),
        overall_confidence=0.95,
    )

    assert result.priority == DecisionPriority.INSUFFICIENT_DATA
    assert result.decision_score is None
    assert result.factors == []


def test_disqualified_guardrail_forces_low_priority_even_with_strong_signals():
    disqualification = make_disqualification(
        final_decision="disqualified", category=DisqualificationCategory.GENUINE_NEGATIVE_EVIDENCE
    )
    result = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=95.0, confidence=0.95),
        disqualification=disqualification,
        buying_intent=make_buying_intent(level=BuyingIntentLevel.STRONG, score=1.0),
        contradictions=no_contradictions(),
        why_now=no_why_now(),
        overall_confidence=0.95,
    )

    assert result.priority == DecisionPriority.LOW_PRIORITY
    assert result.decision_score == 0.0


def test_qualified_with_strong_everything_yields_high_priority():
    result = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=95.0, confidence=0.9),
        disqualification=make_disqualification(),
        buying_intent=make_buying_intent(level=BuyingIntentLevel.STRONG, score=1.0),
        contradictions=no_contradictions(),
        why_now=WhyNowExplanation(has_timing_trigger=True, data_sufficient=True, triggers=[], narrative="fresh trigger"),
        overall_confidence=0.9,
    )

    assert result.priority == DecisionPriority.HIGH_PRIORITY
    assert result.decision_score >= 0.7


def test_qualified_with_weak_signals_yields_low_priority():
    result = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=20.0, confidence=0.3),
        disqualification=make_disqualification(),
        buying_intent=make_buying_intent(level=BuyingIntentLevel.NONE, score=0.0),
        contradictions=no_contradictions(),
        why_now=no_why_now(),
        overall_confidence=0.3,
    )

    assert result.priority == DecisionPriority.LOW_PRIORITY


def test_insufficient_data_buying_intent_does_not_count_toward_score():
    """When buying intent itself couldn't be assessed, its value should
    contribute 0 to the decision score rather than silently using
    BuyingIntentAssessment.score (which is 0.0 anyway, but this locks in
    the intent so a future scoring change on that field can't regress it)."""
    result_insufficient = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=50.0, confidence=0.5),
        disqualification=make_disqualification(),
        buying_intent=BuyingIntentAssessment(
            level=BuyingIntentLevel.INSUFFICIENT_DATA, score=0.0, matched_signals=[], rationale="thin coverage"
        ),
        contradictions=no_contradictions(),
        why_now=no_why_now(),
        overall_confidence=0.5,
    )
    result_none = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=50.0, confidence=0.5),
        disqualification=make_disqualification(),
        buying_intent=make_buying_intent(level=BuyingIntentLevel.NONE, score=0.0),
        contradictions=no_contradictions(),
        why_now=no_why_now(),
        overall_confidence=0.5,
    )
    assert result_insufficient.decision_score == result_none.decision_score


def test_contradictions_reduce_decision_score():
    baseline = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=70.0, confidence=0.7),
        disqualification=make_disqualification(),
        buying_intent=make_buying_intent(),
        contradictions=no_contradictions(),
        why_now=no_why_now(),
        overall_confidence=0.7,
    )
    with_contradiction = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=70.0, confidence=0.7),
        disqualification=make_disqualification(),
        buying_intent=make_buying_intent(),
        contradictions=ContradictionReport(
            has_contradictions=True,
            findings=[
                ContradictionFinding(
                    theme="hiring_trajectory",
                    severity=ContradictionSeverity.HIGH,
                    description="d",
                    evidence_a=ContradictionEvidenceRef(label="a", excerpt="a", source="s"),
                    evidence_b=ContradictionEvidenceRef(label="b", excerpt="b", source="s"),
                )
            ],
            summary="1 contradiction",
        ),
        why_now=no_why_now(),
        overall_confidence=0.7,
    )

    assert with_contradiction.decision_score < baseline.decision_score


def test_why_now_trigger_boosts_decision_score():
    baseline = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=60.0, confidence=0.6),
        disqualification=make_disqualification(),
        buying_intent=make_buying_intent(),
        contradictions=no_contradictions(),
        why_now=no_why_now(),
        overall_confidence=0.6,
    )
    with_trigger = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=60.0, confidence=0.6),
        disqualification=make_disqualification(),
        buying_intent=make_buying_intent(),
        contradictions=no_contradictions(),
        why_now=WhyNowExplanation(has_timing_trigger=True, data_sufficient=True, triggers=[], narrative="fresh"),
        overall_confidence=0.6,
    )

    assert with_trigger.decision_score > baseline.decision_score


def test_decision_score_never_exceeds_one_or_drops_below_zero():
    result = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=100.0, confidence=1.0),
        disqualification=make_disqualification(),
        buying_intent=make_buying_intent(level=BuyingIntentLevel.STRONG, score=1.0),
        contradictions=no_contradictions(),
        why_now=WhyNowExplanation(has_timing_trigger=True, data_sufficient=True, triggers=[], narrative="fresh"),
        overall_confidence=1.0,
    )
    assert 0.0 <= result.decision_score <= 1.0


def test_factors_list_is_populated_for_qualified_decisions_for_traceability():
    result = DecisionEngine().decide(
        purchase_result=make_purchase_result(score=70.0, confidence=0.7),
        disqualification=make_disqualification(),
        buying_intent=make_buying_intent(),
        contradictions=no_contradictions(),
        why_now=no_why_now(),
        overall_confidence=0.7,
    )
    factor_names = {f.name for f in result.factors}
    assert {"purchase_score", "buying_intent", "confidence", "why_now_boost", "contradiction_penalty"} == factor_names
