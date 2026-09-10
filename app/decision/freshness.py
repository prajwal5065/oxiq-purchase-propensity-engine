"""Freshness Assessment (Decision Intelligence primitive).

Turns a raw `published_at` timestamp into a labeled freshness judgment a
human can act on ("this is a live signal from this week" vs "this is a
year-old data point"), by delegating entirely to
`app.scoring.time_decay.classify` - the single source of truth for both
the label and the weight - so freshness reads consistently everywhere in
the system rather than having a second, diverging notion of "recent."

Evidence with no `published_at` is never treated as fresh or stale - it's
UNKNOWN, matching time_decay's UNKNOWN_RECENCY_WEIGHT. Decision Intelligence
must never quietly assume an undated signal is either urgent or dormant.
"""
from datetime import datetime

from app.schemas.decision import FreshnessAssessment, FreshnessLabelLiteral
from app.schemas.evidence import EvidenceItem
from app.scoring.time_decay import classify as _classify


def classify(published_at: datetime | None, now: datetime | None = None) -> tuple[FreshnessLabelLiteral, float]:
    """Thin re-export of time_decay.classify, kept here for callers that
    already import `freshness.classify` - see that module for the bucket
    definitions (current/recent/aging/stale/historical/unknown)."""
    return _classify(published_at, now)


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
