import pytest

from app.models.score import ScoreType
from app.rules.engine import RuleEngine
from app.schemas.score import PillarScore


def pillar(score_type: ScoreType, score: float, confidence: float = 0.8) -> PillarScore:
    return PillarScore(score_type=score_type, score=score, confidence=confidence, reasons=[])


def full_pillar_set(capacity: float = 60, need: float = 60) -> list[PillarScore]:
    return [
        pillar(ScoreType.NEED, need),
        pillar(ScoreType.URGENCY, 60),
        pillar(ScoreType.CAPACITY, capacity),
        pillar(ScoreType.DIGITAL_MATURITY, 60),
        pillar(ScoreType.ORG_READINESS, 60),
        pillar(ScoreType.WINNABILITY, 60),
    ]


def test_low_capacity_triggers_penalty():
    engine = RuleEngine()
    result = engine.evaluate(pillar_scores=full_pillar_set(capacity=10), purchase_score=60.0)
    assert not result.disqualified
    assert result.adjusted_score == 30.0  # 60 * 0.5
    assert any("Capacity" in r or "capacity" in r for r in result.applied_adjustments)


def test_no_adjustment_when_thresholds_not_met():
    engine = RuleEngine()
    result = engine.evaluate(pillar_scores=full_pillar_set(), purchase_score=60.0)
    assert result.adjusted_score == 60.0
    assert result.applied_adjustments == []


def test_disqualifier_zeroes_out_score():
    engine = RuleEngine()
    zero_confidence_pillars = [
        PillarScore(score_type=t, score=0, confidence=0, reasons=[])
        for t in [
            ScoreType.NEED,
            ScoreType.URGENCY,
            ScoreType.CAPACITY,
            ScoreType.DIGITAL_MATURITY,
            ScoreType.ORG_READINESS,
            ScoreType.WINNABILITY,
        ]
    ]
    result = engine.evaluate(pillar_scores=zero_confidence_pillars, purchase_score=60.0)
    assert result.disqualified
    assert result.adjusted_score == 0.0
    assert result.disqualified_reason


def test_confidence_factor_reflects_signal_coverage():
    engine = RuleEngine()
    partial_pillars = full_pillar_set()
    partial_pillars[0] = pillar(ScoreType.NEED, 0, confidence=0)  # one pillar has no evidence
    result = engine.evaluate(pillar_scores=partial_pillars, purchase_score=60.0)
    assert result.confidence_factor == pytest.approx(5 / 6, rel=0.01)


def test_unknown_industry_uses_default_prior():
    engine = RuleEngine()
    result = engine.evaluate(pillar_scores=full_pillar_set(), purchase_score=60.0, industry="Widget Making")
    assert result.industry_prior == 1.0
