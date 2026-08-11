from datetime import UTC, datetime, timedelta

from app.decision.freshness import FreshnessEngine, classify
from app.schemas.evidence import EvidenceItem


def make_evidence(published_at=None):
    return EvidenceItem(
        signal_label="x", excerpt="y", source="z", confidence=0.8, published_at=published_at
    )


def test_classify_labels_within_a_week_as_very_fresh():
    now = datetime(2026, 1, 10, tzinfo=UTC)
    label, weight = classify(now - timedelta(days=3), now=now)
    assert label == "very_fresh"
    assert weight == 1.0


def test_classify_labels_within_90_days_as_recent():
    now = datetime(2026, 1, 10, tzinfo=UTC)
    label, weight = classify(now - timedelta(days=45), now=now)
    assert label == "recent"
    assert weight == 0.7


def test_classify_labels_within_a_year_as_aging():
    now = datetime(2026, 1, 10, tzinfo=UTC)
    label, weight = classify(now - timedelta(days=200), now=now)
    assert label == "aging"
    assert weight == 0.4


def test_classify_labels_older_than_a_year_as_stale():
    now = datetime(2026, 1, 10, tzinfo=UTC)
    label, weight = classify(now - timedelta(days=800), now=now)
    assert label == "stale"
    assert weight == 0.1


def test_classify_labels_missing_date_as_unknown_not_fresh_or_stale():
    label, weight = classify(None)
    assert label == "unknown"
    assert weight == 0.5


def test_freshness_engine_assess_returns_evidence_id_and_published_at():
    now = datetime(2026, 1, 10, tzinfo=UTC)
    item = make_evidence(published_at=now - timedelta(days=1))
    assessment = FreshnessEngine().assess(item, now=now)

    assert assessment.evidence_id == item.id
    assert assessment.label == "very_fresh"
    assert assessment.published_at == item.published_at


def test_freshness_engine_assess_batch_preserves_order():
    now = datetime(2026, 1, 10, tzinfo=UTC)
    items = [
        make_evidence(published_at=now - timedelta(days=1)),
        make_evidence(published_at=now - timedelta(days=500)),
        make_evidence(published_at=None),
    ]
    results = FreshnessEngine().assess_batch(items, now=now)

    assert [r.label for r in results] == ["very_fresh", "stale", "unknown"]


def test_classify_handles_naive_datetime_without_raising():
    now = datetime(2026, 1, 10, tzinfo=UTC)
    naive_published = datetime(2026, 1, 5)  # noqa: DTZ001 - deliberately naive, exercising the fallback
    label, weight = classify(naive_published, now=now)
    assert label == "very_fresh"
    assert weight == 1.0
