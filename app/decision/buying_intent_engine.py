"""Buying Intent Engine (Decision Intelligence).

Distinguishes evidence that signals active purchase intent - budget
approved, vendors being evaluated, a pilot underway - from the softer
"need"/"urgency" signals the baseline scorers already look for. Buying
intent is specifically about *procurement motion*, not just "this company
has a problem we could solve."

Guardrail: mirrors DisqualificationEngine's core rule (spec: "Do not claim
low buying intent simply because data collection failed"). A company with
no detected buying-intent language is only reported as NONE when there was
actually enough evidence coverage to make that call; when coverage was too
thin to look properly, the level is INSUFFICIENT_DATA instead - "we looked
and saw no buying signals" and "we couldn't look for buying signals" must
never collapse into the same conclusion.
"""
from app.schemas.decision import BuyingIntentAssessment, BuyingIntentLevel, BuyingIntentSignal
from app.schemas.evidence import EvidenceItem

# (phrase, strength) - checked case-insensitively against "label + excerpt".
# STRONG: near-unambiguous procurement motion. MODERATE: an evaluation/
# investment signal that often precedes procurement. WEAK: early-stage
# interest that may or may not turn into a purchase.
_STRONG_SIGNALS = [
    "request for proposal",
    "rfp",
    "evaluating vendors",
    "vendor evaluation",
    "budget approved",
    "purchase order",
    "signed contract",
    "vendor selection",
    "proof of concept",
    "poc",
    "pilot program",
    "shortlisted",
]
_MODERATE_SIGNALS = [
    "hiring ai engineer",
    "hiring machine learning",
    "expanding team",
    "new budget",
    "investing in ai",
    "digital transformation initiative",
    "seeking proposals",
    "comparing solutions",
]
_WEAK_SIGNALS = [
    "exploring ai",
    "interested in automation",
    "considering options",
    "researching solutions",
    "looking into",
]

_LEVEL_SCORE: dict[BuyingIntentLevel, float] = {
    BuyingIntentLevel.STRONG: 1.0,
    BuyingIntentLevel.MODERATE: 0.6,
    BuyingIntentLevel.WEAK: 0.3,
    BuyingIntentLevel.NONE: 0.0,
}

# Coverage below this means "we didn't look enough," not "we looked and
# found nothing" - matches DisqualificationEngine's GENUINE_LOOK thresholds
# so the two guardrails agree on what counts as a genuine look.
MIN_COVERAGE_FOR_GENUINE_LOOK = 0.5
MIN_EVIDENCE_FOR_GENUINE_LOOK = 3

MAX_SIGNALS_RETURNED = 8


class BuyingIntentEngine:
    def assess(
        self,
        evidence: list[EvidenceItem],
        coverage_percentage: float,
        evidence_items_accepted: int,
    ) -> BuyingIntentAssessment:
        had_genuine_look = (
            coverage_percentage >= MIN_COVERAGE_FOR_GENUINE_LOOK
            and evidence_items_accepted >= MIN_EVIDENCE_FOR_GENUINE_LOOK
        )

        strong = self._match(evidence, _STRONG_SIGNALS, "strong")
        moderate = self._match(evidence, _MODERATE_SIGNALS, "moderate")
        weak = self._match(evidence, _WEAK_SIGNALS, "weak")
        matched = strong + moderate + weak

        if not matched and not had_genuine_look:
            return BuyingIntentAssessment(
                level=BuyingIntentLevel.INSUFFICIENT_DATA,
                score=0.0,
                matched_signals=[],
                rationale=(
                    "Evidence coverage was too thin to assess buying intent - absence of "
                    "detected signals here reflects limited data collection, not confirmed low intent."
                ),
            )

        if strong:
            level = BuyingIntentLevel.STRONG
        elif moderate:
            level = BuyingIntentLevel.MODERATE
        elif weak:
            level = BuyingIntentLevel.WEAK
        else:
            level = BuyingIntentLevel.NONE

        return BuyingIntentAssessment(
            level=level,
            score=_LEVEL_SCORE[level],
            matched_signals=matched[:MAX_SIGNALS_RETURNED],
            rationale=self._rationale(level, matched),
        )

    @staticmethod
    def _match(evidence: list[EvidenceItem], phrases: list[str], strength: str) -> list[BuyingIntentSignal]:
        lowered = [p.lower() for p in phrases]
        signals: list[BuyingIntentSignal] = []
        for item in evidence:
            haystack = f"{item.signal_label} {item.excerpt}".lower()
            if any(p in haystack for p in lowered):
                signals.append(
                    BuyingIntentSignal(
                        evidence_id=item.id,
                        label=item.signal_label,
                        excerpt=item.excerpt,
                        source=item.source,
                        strength=strength,
                    )
                )
        return signals

    @staticmethod
    def _rationale(level: BuyingIntentLevel, matched: list[BuyingIntentSignal]) -> str:
        if level == BuyingIntentLevel.NONE:
            return "Evidence coverage was sufficient but no procurement-motion language was detected."
        return f"{len(matched)} evidence item(s) matched {level.value}-strength buying-intent language."
