"""Age-based decay weighting for time-sensitive signals (urgency).

A simple bucket function, per spec: "A simple decay function or age-based
buckets are sufficient for the first version." Unknown recency (no
`published_at` on the evidence) is treated as moderate weight - not
assumed fresh, not assumed stale, since we genuinely don't know.
"""
from datetime import UTC, datetime

# (max_age_in_days, weight) - first bucket whose max_age the signal fits wins.
DECAY_BUCKETS: list[tuple[int, float]] = [
    (7, 1.0),  # this week - very high
    (90, 0.7),  # within 3 months - medium
    (365, 0.4),  # within 1 year - low
    (10**6, 0.1),  # older than a year - minimal
]

UNKNOWN_RECENCY_WEIGHT = 0.5


def decay_weight(published_at: datetime | None, now: datetime | None = None) -> float:
    """Return a 0-1 weight for how much a signal should count toward urgency,
    based on its age. Unknown publish date returns UNKNOWN_RECENCY_WEIGHT."""
    if published_at is None:
        return UNKNOWN_RECENCY_WEIGHT

    reference = now or datetime.now(UTC)
    published = published_at if published_at.tzinfo else published_at.replace(tzinfo=UTC)
    age_days = max((reference - published).days, 0)

    for max_age_days, weight in DECAY_BUCKETS:
        if age_days <= max_age_days:
            return weight
    return DECAY_BUCKETS[-1][1]
