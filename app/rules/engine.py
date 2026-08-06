"""Rule Engine.

Scoring agents only calculate pillar scores. Business rules - the things a
sales/ops person would want to tune without touching scorer code - live
here, driven entirely by `default_rules.json`. Swap that file (or point
`RuleEngine` at a different path) to change behavior with no code changes.
"""
import json
import operator as op
from pathlib import Path

from app.rules.schemas import RuleCondition, RuleEngineConfig, RuleOperator
from app.schemas.score import PillarScore

_OPERATORS = {
    RuleOperator.LT: op.lt,
    RuleOperator.LTE: op.le,
    RuleOperator.GT: op.gt,
    RuleOperator.GTE: op.ge,
    RuleOperator.EQ: op.eq,
}

DEFAULT_CONFIG_PATH = Path(__file__).parent / "default_rules.json"


class RuleEngineResult:
    def __init__(
        self,
        disqualified: bool,
        disqualified_reason: str | None,
        adjusted_score: float,
        applied_adjustments: list[str],
        confidence_factor: float,
        industry_prior: float,
    ) -> None:
        self.disqualified = disqualified
        self.disqualified_reason = disqualified_reason
        self.adjusted_score = adjusted_score
        self.applied_adjustments = applied_adjustments
        self.confidence_factor = confidence_factor
        self.industry_prior = industry_prior


class RuleEngine:
    def __init__(self, config_path: Path | str | None = None) -> None:
        path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = RuleEngineConfig.model_validate(json.loads(path.read_text()))

    def evaluate(
        self,
        pillar_scores: list[PillarScore],
        purchase_score: float,
        industry: str | None = None,
    ) -> RuleEngineResult:
        context = self._build_context(pillar_scores)

        disqualified, reason = self._evaluate_disqualifiers(context)

        adjusted_score = purchase_score
        applied: list[str] = []
        if not disqualified:
            adjusted_score, applied = self._apply_adjustments(adjusted_score, context)

        confidence_factor = self._compute_confidence_factor(pillar_scores)
        industry_prior = self._compute_industry_prior(industry)

        if not disqualified:
            adjusted_score = round(min(adjusted_score * industry_prior, 100.0), 1)

        return RuleEngineResult(
            disqualified=disqualified,
            disqualified_reason=reason,
            adjusted_score=0.0 if disqualified else adjusted_score,
            applied_adjustments=applied,
            confidence_factor=confidence_factor,
            industry_prior=industry_prior,
        )

    @staticmethod
    def _build_context(pillar_scores: list[PillarScore]) -> dict[str, float]:
        context = {p.score_type.value: p.score for p in pillar_scores}
        non_zero_confidence = sum(1 for p in pillar_scores if p.confidence > 0)
        context["overall_confidence"] = (
            round(non_zero_confidence / len(pillar_scores), 2) if pillar_scores else 0.0
        )
        return context

    @staticmethod
    def _check(condition: RuleCondition, context: dict[str, float]) -> bool:
        if condition.field not in context:
            return False
        return _OPERATORS[condition.operator](context[condition.field], condition.value)

    def _evaluate_disqualifiers(self, context: dict[str, float]) -> tuple[bool, str | None]:
        for rule in self.config.disqualifiers:
            if self._check(rule.condition, context):
                return True, rule.description
        return False, None

    def _apply_adjustments(
        self, purchase_score: float, context: dict[str, float]
    ) -> tuple[float, list[str]]:
        score = purchase_score
        applied: list[str] = []
        for rule in self.config.adjustments:
            if not self._check(rule.condition, context):
                continue
            if rule.action == "multiply":
                score *= rule.action_value
            elif rule.action == "cap":
                score = min(score, rule.action_value)
            elif rule.action == "floor":
                score = max(score, rule.action_value)
            applied.append(rule.description)
        return round(max(min(score, 100.0), 0.0), 1), applied

    @staticmethod
    def _compute_confidence_factor(pillar_scores: list[PillarScore]) -> float:
        """Signal coverage: what fraction of pillars actually had matched
        evidence. Low coverage means the overall confidence should be
        discounted even if the pillars that DID match look strong."""
        if not pillar_scores:
            return 0.0
        covered = sum(1 for p in pillar_scores if p.confidence > 0)
        return round(covered / len(pillar_scores), 2)

    def _compute_industry_prior(self, industry: str | None) -> float:
        if not industry:
            return self.config.default_industry_prior
        for prior in self.config.industry_priors:
            if prior.industry.lower() == industry.lower():
                return prior.multiplier
        return self.config.default_industry_prior
