"""Decision Engine (Decision Intelligence).

The final synthesis step: combines the purchase score, buying intent,
contradictions, and why-now timing into one outreach priority. Two
guardrails take precedence over every computed number:

1. If the Disqualification Engine already concluded `insufficient_data`,
   the decision here is INSUFFICIENT_DATA too, full stop - a Decision
   Engine that computed its own confident-looking priority on top of data
   the system already flagged as too thin would just re-hide the same
   problem one layer up.
2. If disqualified for a genuine business reason, the priority is
   LOW_PRIORITY - never upgraded by buying-intent or why-now signals,
   since a disqualifying condition (e.g. capacity too low) is a hard
   business conclusion, not one factor to average against others.

Everywhere else, this produces a 0-1 decision_score from weighted factors
and maps it to a priority tier, with every factor listed so the score is
never a black box.
"""
from app.schemas.decision import (
    BuyingIntentAssessment,
    BuyingIntentLevel,
    ContradictionReport,
    DecisionFactor,
    DecisionPriority,
    DecisionRecommendation,
    WhyNowExplanation,
)
from app.schemas.explanation import DisqualificationExplanation
from app.schemas.score import PurchaseScoreResult

_WEIGHTS = {
    "purchase_score": 0.45,
    "buying_intent": 0.30,
    "confidence": 0.15,
}
_WHY_NOW_BOOST = 0.10
_CONTRADICTION_PENALTY_PER_FINDING = 0.10
_MAX_CONTRADICTION_PENALTY = 0.25

HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.4


class DecisionEngine:
    def decide(
        self,
        purchase_result: PurchaseScoreResult,
        disqualification: DisqualificationExplanation,
        buying_intent: BuyingIntentAssessment,
        contradictions: ContradictionReport,
        why_now: WhyNowExplanation,
        overall_confidence: float,
    ) -> DecisionRecommendation:
        if disqualification.final_decision == "insufficient_data":
            return DecisionRecommendation(
                priority=DecisionPriority.INSUFFICIENT_DATA,
                decision_score=None,
                factors=[],
                rationale=(
                    "Data collection was insufficient to reach any priority decision: "
                    f"{disqualification.primary_reason}"
                ),
                buying_intent=buying_intent,
                contradictions=contradictions,
                why_now=why_now,
            )

        if disqualification.final_decision == "disqualified":
            return DecisionRecommendation(
                priority=DecisionPriority.LOW_PRIORITY,
                decision_score=0.0,
                factors=[],
                rationale=(
                    f"Disqualified on the merits, not on missing data: {disqualification.primary_reason}"
                ),
                buying_intent=buying_intent,
                contradictions=contradictions,
                why_now=why_now,
            )

        factors = self._build_factors(purchase_result, buying_intent, contradictions, why_now, overall_confidence)
        decision_score = round(min(max(sum(f.value * f.weight for f in factors), 0.0), 1.0), 2)
        priority = self._priority(decision_score)

        return DecisionRecommendation(
            priority=priority,
            decision_score=decision_score,
            factors=factors,
            rationale=self._rationale(priority, decision_score, buying_intent, contradictions, why_now),
            buying_intent=buying_intent,
            contradictions=contradictions,
            why_now=why_now,
        )

    def _build_factors(
        self,
        purchase_result: PurchaseScoreResult,
        buying_intent: BuyingIntentAssessment,
        contradictions: ContradictionReport,
        why_now: WhyNowExplanation,
        overall_confidence: float,
    ) -> list[DecisionFactor]:
        buying_intent_value = (
            buying_intent.score if buying_intent.level != BuyingIntentLevel.INSUFFICIENT_DATA else 0.0
        )
        contradiction_penalty = min(
            len(contradictions.findings) * _CONTRADICTION_PENALTY_PER_FINDING, _MAX_CONTRADICTION_PENALTY
        )
        why_now_boost = _WHY_NOW_BOOST if why_now.has_timing_trigger else 0.0

        return [
            DecisionFactor(
                name="purchase_score",
                value=round(purchase_result.purchase_score / 100, 2),
                weight=_WEIGHTS["purchase_score"],
                description="Aggregate purchase-propensity score across all pillars",
            ),
            DecisionFactor(
                name="buying_intent",
                value=round(buying_intent_value, 2),
                weight=_WEIGHTS["buying_intent"],
                description=f"Buying-intent level: {buying_intent.level.value}",
            ),
            DecisionFactor(
                name="confidence",
                value=overall_confidence,
                weight=_WEIGHTS["confidence"],
                description="Overall analysis confidence",
            ),
            DecisionFactor(
                name="why_now_boost",
                value=why_now_boost,
                weight=1.0,
                description="Flat boost applied when a fresh timing trigger was found",
            ),
            DecisionFactor(
                name="contradiction_penalty",
                value=-contradiction_penalty,
                weight=1.0,
                description=f"Flat penalty for {len(contradictions.findings)} unresolved contradiction(s)",
            ),
        ]

    @staticmethod
    def _priority(decision_score: float) -> DecisionPriority:
        if decision_score >= HIGH_THRESHOLD:
            return DecisionPriority.HIGH_PRIORITY
        if decision_score >= MEDIUM_THRESHOLD:
            return DecisionPriority.MEDIUM_PRIORITY
        return DecisionPriority.LOW_PRIORITY

    @staticmethod
    def _rationale(
        priority: DecisionPriority,
        decision_score: float,
        buying_intent: BuyingIntentAssessment,
        contradictions: ContradictionReport,
        why_now: WhyNowExplanation,
    ) -> str:
        parts = [f"Decision score {decision_score:.0%} -> {priority.value.replace('_', ' ')}."]
        parts.append(f"Buying intent: {buying_intent.level.value}.")
        if contradictions.has_contradictions:
            parts.append(f"{len(contradictions.findings)} contradiction(s) discounted the score.")
        if why_now.has_timing_trigger:
            parts.append("A fresh timing trigger boosted the score.")
        return " ".join(parts)
