"""Age-based decay weighting for time-sensitive signals.

A simple bucket function, per spec: "A simple decay function or age-based
buckets are sufficient for the first version." Unknown recency (no
`published_at` on the evidence) is treated as moderate weight - not
assumed fresh, not assumed stale, since we genuinely don't know.

This is the single source of truth for both the numeric decay weight
(used by every scoring agent to discount old evidence) and the
human-readable freshness label (`app/decision/freshness.py`) - they used
to be defined separately and could drift out of sync with each other.

Five buckets, not four: evidence within the last year decays gradually
(current -> recent -> aging), but everything beyond a year used to
collapse into one flat "older than a year" bucket with a single weight.
That meant a 13-month-old signal and an 8-year-old signal (e.g. a
2016-2019 press mention) counted identically - which is exactly the kind
of stale evidence dominating a report the way recent evidence should.
"Stale" (1-2 years) and "historical" (2+ years) are now split, with
historical evidence weighted low enough that it can inform context
without materially moving a pillar score.
"""
from datetime import UTC, datetime

from typing import Literal

FreshnessLabel = Literal["very_fresh", "recent", "aging", "stale", "historical", "unknown"]

# (max_age_in_days, weight, label) - first bucket whose max_age the signal
# fits wins. "very_fresh"/"recent" are the "Current/Recent Signal" tier,
# "aging"/"stale" are borderline, "historical" is the "Historical Context"
# tier that should barely move a score.
DECAY_BUCKETS: list[tuple[int, float, FreshnessLabel]] = [
    (7, 1.0, "very_fresh"),  # this week - very high
    (90, 0.7, "recent"),  # within 3 months - medium-high
    (365, 0.4, "aging"),  # within 1 year - low-medium
    (730, 0.15, "stale"),  # 1-2 years - low
    (10**6, 0.05, "historical"),  # 2+ years (e.g. a 2016-2019 mention) - minimal
]

UNKNOWN_RECENCY_WEIGHT = 0.5


def decay_weight(published_at: datetime | None, now: datetime | None = None) -> float:
    """Return a 0-1 weight for how much a signal should count, based on its
    age. Unknown publish date returns UNKNOWN_RECENCY_WEIGHT."""
    return classify(published_at, now)[1]


def classify(published_at: datetime | None, now: datetime | None = None) -> tuple[FreshnessLabel, float]:
    """Return (label, weight) for a single timestamp - the shared logic
    every caller (scorers, FreshnessEngine, EvidenceConfidenceEngine)
    should use, so the label and the weight can never drift apart."""
    if published_at is None:
        return "unknown", UNKNOWN_RECENCY_WEIGHT

    reference = now or datetime.now(UTC)
    published = published_at if published_at.tzinfo else published_at.replace(tzinfo=UTC)
    age_days = max((reference - published).days, 0)

    for max_age_days, weight, label in DECAY_BUCKETS:
        if age_days <= max_age_days:
            return label, weight
    return DECAY_BUCKETS[-1][2], DECAY_BUCKETS[-1][1]
