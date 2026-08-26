import pytest

from app.aggregation.purchase_aggregator import PurchaseAggregator
from app.models.score import ScoreType
from app.schemas.score import PillarScore


def pillar(score_type: ScoreType, score: float, confidence: float = 0.8, reasons=None) -> PillarScore:
    return PillarScore(score_type=score_type, score=score, confidence=confidence, reasons=reasons or [])


def test_weighted_sum_matches_spec_weights():
    # All pillars at 100 -> aggregate should be 100 (weights sum to 1.0)
    pillars = [
        pillar(ScoreType.NEED, 100),
        pillar(ScoreType.URGENCY, 100),
        pillar(ScoreType.CAPACITY, 100),
        pillar(ScoreType.DIGITAL_MATURITY, 100),
        pillar(ScoreType.ORG_READINESS, 100),
        pillar(ScoreType.WINNABILITY, 100),
    ]
    result = PurchaseAggregator().aggregate("acme.com", pillars)
    assert result.purchase_score == 100.0
    assert not result.disqualified


def test_only_need_pillar_scores_reflects_its_30pct_weight():
    """Capacity/Urgency/etc. here are 0 with confidence=0 - no evidence was
    found, not evidence of a genuine problem. That must NOT trip the "low
    capacity" penalty (missing evidence != negative evidence) - the result
    should be exactly Need's 30% weighted contribution, unpenalized."""
    pillars = [
        pillar(ScoreType.NEED, 100),
        pillar(ScoreType.URGENCY, 0, confidence=0),
        pillar(ScoreType.CAPACITY, 0, confidence=0),
        pillar(ScoreType.DIGITAL_MATURITY, 0, confidence=0),
        pillar(ScoreType.ORG_READINESS, 0, confidence=0),
        pillar(ScoreType.WINNABILITY, 0, confidence=0),
    ]
    result = PurchaseAggregator().aggregate("acme.com", pillars)
    assert result.purchase_score == pytest.approx(30.0, abs=0.5)
    assert "capacity" in result.pillar_scores[2].score_type.value


def test_confidently_low_capacity_still_triggers_penalty():
    """The flip side: when Capacity is genuinely, confidently assessed as
    low (real evidence, not an absence of it), the penalty must still
    fire - this isn't a blanket exemption for low scores, only for
    unevidenced ones."""
    pillars = [
        pillar(ScoreType.NEED, 100),
        pillar(ScoreType.URGENCY, 0, confidence=0),
        pillar(ScoreType.CAPACITY, 5, confidence=0.8, reasons=["Tiny team: 3 employees"]),
        pillar(ScoreType.DIGITAL_MATURITY, 0, confidence=0),
        pillar(ScoreType.ORG_READINESS, 0, confidence=0),
        pillar(ScoreType.WINNABILITY, 0, confidence=0),
    ]
    result = PurchaseAggregator().aggregate("acme.com", pillars)
    # Weighted sum: Need 30 + Capacity 5*0.15=0.75 = 30.75, halved by the
    # confidently-low-capacity penalty.
    assert result.purchase_score == pytest.approx(15.4, abs=0.5)
    assert result.purchase_score < 30.0


def test_disqualified_when_no_evidence_anywhere():
    pillars = [
        pillar(t, 0, confidence=0)
        for t in [
            ScoreType.NEED,
            ScoreType.URGENCY,
            ScoreType.CAPACITY,
            ScoreType.DIGITAL_MATURITY,
            ScoreType.ORG_READINESS,
            ScoreType.WINNABILITY,
        ]
    ]
    result = PurchaseAggregator().aggregate("acme.com", pillars)
    assert result.disqualified
    assert result.purchase_score == 0.0
