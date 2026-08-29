"""Purchase Aggregator.

Combines the six pillar scores into a single weighted Purchase Propensity
Score, then hands it to the Rule Engine for disqualifiers, configurable
adjustments, confidence-factor discounting, and industry-prior calibration.

Weights match the spec:
    Need 30% / Urgency 20% / Capacity 15% / Digital Maturity 15%
    / Organization Readiness 10% / Winnability 10%
"""
from app.models.score import ScoreType
from app.rules.engine import RuleEngine
from app.schemas.score import PillarScore, PurchaseScoreResult

DEFAULT_WEIGHTS: dict[ScoreType, float] = {
    ScoreType.NEED: 0.30,
    ScoreType.URGENCY: 0.20,
    ScoreType.CAPACITY: 0.15,
    ScoreType.DIGITAL_MATURITY: 0.15,
    ScoreType.ORG_READINESS: 0.10,
    ScoreType.WINNABILITY: 0.10,
}


class PurchaseAggregator:
    def __init__(
        self,
        rule_engine: RuleEngine | None = None,
        weights: dict[ScoreType, float] | None = None,
    ) -> None:
        self.rule_engine = rule_engine or RuleEngine()
        self.weights = weights or DEFAULT_WEIGHTS

    def aggregate(
        self,
        company_domain: str,
        pillar_scores: list[PillarScore],
        industry: str | None = None,
    ) -> PurchaseScoreResult:
        raw_weighted_score = self._weighted_sum(pillar_scores)

        rule_result = self.rule_engine.evaluate(
            pillar_scores=pillar_scores, purchase_score=raw_weighted_score, industry=industry
        )

        base_confidence = self._weighted_confidence(pillar_scores)
        overall_confidence = round(
            min(base_confidence * rule_result.confidence_factor, 1.0), 2
        )

        evidence_summary = [
            reason
            for pillar in sorted(pillar_scores, key=lambda p: p.score, reverse=True)
            for reason in pillar.reasons[:2]
        ][:8]

        return PurchaseScoreResult(
            company_domain=company_domain,
            pillar_scores=pillar_scores,
            purchase_score=rule_result.adjusted_score,
            confidence=overall_confidence,
            evidence_summary=evidence_summary,
            disqualified=rule_result.disqualified,
            disqualified_reason=rule_result.disqualified_reason,
            applied_adjustments=rule_result.applied_adjustments,
        )

    def _weighted_sum(self, pillar_scores: list[PillarScore]) -> float:
        total = 0.0
        for pillar in pillar_scores:
            weight = self.weights.get(pillar.score_type, 0.0)
            total += pillar.score * weight
        return round(total, 1)

    @staticmethod
    def _weighted_confidence(pillar_scores: list[PillarScore]) -> float:
        """Confidence weighted by how much each pillar counts toward the
        final score, so a confident-but-minor pillar can't inflate overall
        confidence as much as a confident-and-major one."""
        total_weight = sum(DEFAULT_WEIGHTS.get(p.score_type, 0.0) for p in pillar_scores)
        if total_weight == 0:
            return 0.0
        weighted = sum(
            p.confidence * DEFAULT_WEIGHTS.get(p.score_type, 0.0) for p in pillar_scores
        )
        return round(weighted / total_weight, 2)
