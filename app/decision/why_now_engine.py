"""Why Now Engine (Decision Intelligence).

Surfaces the specific, dated events that make *this moment* a good time to
reach out - a funding round announced last week matters to timing in a way
a two-year-old one doesn't, even though both might count toward the
Urgency pillar score. This engine doesn't recompute urgency; it picks out
the freshest trigger-worthy evidence and turns it into a short narrative a
salesperson can lead with.

`data_sufficient` distinguishes "we checked and nothing recent qualifies"
from "there was no evidence to check at all" - the same insufficient-data
guardrail the rest of Decision Intelligence applies, kept explicit here so
the Decision Engine never reads an empty trigger list as a confident "no."
"""
from datetime import UTC, datetime

from app.decision.freshness import FreshnessEngine
from app.schemas.decision import WhyNowExplanation, WhyNowTrigger
from app.schemas.evidence import EvidenceItem

_TRIGGER_PHRASES: dict[str, list[str]] = {
    "funding_event": ["funding round", "raises", "series a", "series b", "series c"],
    "leadership_change": ["new ceo", "new cto", "appoints", "hires chief", "joins as"],
    "expansion": ["expansion", "new office", "opens office"],
    "product_launch": ["product launch", "unveils", "launches"],
    "acquisition": ["acquisition", "acquires", "acquired"],
    "hiring_spike": ["hiring spike", "hiring surge", "expanding team"],
    # Order/contract-award and deployment/rollout events - a company that
    # just placed a large order or is actively deploying something is
    # exactly the kind of dated, time-sensitive event this engine exists
    # to surface, but neither was represented in any group above.
    "deployment": ["deploys", "deployment of", "rolls out", "rollout of", "delivery of"],
    "order_or_contract": ["places order", "awarded contract", "wins contract", "order for"],
}

# A trigger only counts as "why now" if it's at least this fresh (matches
# time_decay's "within 90 days -> 0.7" bucket) - older evidence might still
# matter for scoring, but it's not a timing trigger for outreach *today*.
MIN_TRIGGER_FRESHNESS_WEIGHT = 0.7
MAX_TRIGGERS = 5

_EPOCH = datetime.min.replace(tzinfo=UTC)


class WhyNowEngine:
    def __init__(self, freshness_engine: FreshnessEngine | None = None) -> None:
        self.freshness_engine = freshness_engine or FreshnessEngine()

    def explain(self, evidence: list[EvidenceItem]) -> WhyNowExplanation:
        triggers = self._find_triggers(evidence)
        triggers.sort(key=lambda t: t.published_at or _EPOCH, reverse=True)
        triggers = triggers[:MAX_TRIGGERS]

        return WhyNowExplanation(
            has_timing_trigger=bool(triggers),
            data_sufficient=bool(evidence),
            triggers=triggers,
            narrative=self._narrative(triggers, bool(evidence)),
        )

    def _find_triggers(self, evidence: list[EvidenceItem]) -> list[WhyNowTrigger]:
        triggers: list[WhyNowTrigger] = []
        for item in evidence:
            trigger_type = self._match_trigger_type(item)
            if trigger_type is None:
                continue
            assessment = self.freshness_engine.assess(item)
            if assessment.weight < MIN_TRIGGER_FRESHNESS_WEIGHT:
                continue
            triggers.append(
                WhyNowTrigger(
                    evidence_id=item.id,
                    label=item.signal_label,
                    excerpt=item.excerpt,
                    source=item.source,
                    trigger_type=trigger_type,
                    published_at=item.published_at,
                    freshness_label=assessment.label,
                )
            )
        return triggers

    @staticmethod
    def _match_trigger_type(item: EvidenceItem) -> str | None:
        haystack = f"{item.signal_label} {item.excerpt}".lower()
        for trigger_type, phrases in _TRIGGER_PHRASES.items():
            if any(p in haystack for p in phrases):
                return trigger_type
        return None

    @staticmethod
    def _narrative(triggers: list[WhyNowTrigger], has_evidence: bool) -> str:
        if triggers:
            lead = triggers[0]
            return (
                f"{lead.trigger_type.replace('_', ' ').title()} evidence ({lead.freshness_label.replace('_', ' ')}) "
                f'makes this a timely moment to reach out: "{lead.label}".'
            )
        if not has_evidence:
            return "No evidence was collected, so no timing trigger could be identified."
        return "No recent (within ~90 days) timing-trigger evidence was found among what was collected."
