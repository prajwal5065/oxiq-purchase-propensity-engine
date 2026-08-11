"""Freshness Assessment (Decision Intelligence primitive).

Turns a raw `published_at` timestamp into a labeled freshness judgment a
human can act on ("this is a live signal from this week" vs "this is a
year-old data point"), reusing the same age-based decay buckets the
Urgency scorer already uses (app/scoring/time_decay.py) so freshness reads
consistently everywhere in the system rather than having a second,
diverging notion of "recent."

Evidence with no `published_at` is never treated as fresh or stale - it's
UNKNOWN, matching time_decay's UNKNOWN_RECENCY_WEIGHT. Decision Intelligence
must never quietly assume an undated signal is either urgent or dormant.
"""
from datetime import UTC, datetime

from app.schemas.decision import FreshnessAssessment, FreshnessLabelLiteral
from app.schemas.evidence import EvidenceItem
from app.scoring.time_decay import decay_weight

_LABEL_BY_MAX_AGE: list[tuple[int, FreshnessLabelLiteral]] = [
    (7, "very_fresh"),
    (90, "recent"),
    (365, "aging"),
]


def classify(published_at: datetime | None, now: datetime | None = None) -> tuple[FreshnessLabelLiteral, float]:
    """Return (label, weight) for a single timestamp - the shared logic
    every caller in this module (and any future one) should use, so the
    label and the weight can never drift apart from each other."""
    weight = decay_weight(published_at, now)
    if published_at is None:
        return "unknown", weight

    reference = now or datetime.now(UTC)
    published = published_at if published_at.tzinfo else published_at.replace(tzinfo=UTC)
    age_days = max((reference - published).days, 0)

    for max_age_days, label in _LABEL_BY_MAX_AGE:
        if age_days <= max_age_days:
            return label, weight
    return "stale", weight


class FreshnessEngine:
    def assess(self, item: EvidenceItem, now: datetime | None = None) -> FreshnessAssessment:
        label, weight = classify(item.published_at, now)
        return FreshnessAssessment(
            evidence_id=item.id,
            label=label,
            weight=weight,
            published_at=item.published_at,
        )

    def assess_batch(self, items: list[EvidenceItem], now: datetime | None = None) -> list[FreshnessAssessment]:
        return [self.assess(item, now) for item in items]
