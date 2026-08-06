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
    pillars = [
        pillar(ScoreType.NEED, 100),
        pillar(ScoreType.URGENCY, 0, confidence=0),
        pillar(ScoreType.CAPACITY, 0, confidence=0),
        pillar(ScoreType.DIGITAL_MATURITY, 0, confidence=0),
        pillar(ScoreType.ORG_READINESS, 0, confidence=0),
        pillar(ScoreType.WINNABILITY, 0, confidence=0),
    ]
    result = PurchaseAggregator().aggregate("acme.com", pillars)
    # Weighted sum is 30 (Need's 30% weight), but Capacity=0 also trips the Rule
    # Engine's "low capacity" adjustment (x0.5), landing on 15.
    assert result.purchase_score == pytest.approx(15.0, abs=0.5)
    assert "capacity" in result.pillar_scores[2].score_type.value


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
