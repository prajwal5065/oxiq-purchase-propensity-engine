from datetime import UTC, datetime, timedelta

from app.schemas.evidence import EvidenceItem
from app.scoring.keyword_matcher import dedupe_events, freshness_weighted_count, match_evidence


def make_evidence(label, excerpt, source="News", category="funding", published_at=None, confidence=0.9):
    return EvidenceItem(
        signal_label=label,
        excerpt=excerpt,
        source=source,
        category=category,
        published_at=published_at,
        confidence=confidence,
    )


def test_dedupe_events_collapses_similar_articles_about_the_same_event():
    now = datetime.now(UTC)
    items = [
        make_evidence("Funding news", "Acme raises $10M in Series A funding round", source="TechCrunch", published_at=now),
        make_evidence("Funding news", "Acme raises $10M in Series A funding round led by XYZ", source="Forbes", published_at=now),
    ]
    deduped = dedupe_events(items)
    assert len(deduped) == 1
    assert "also reported by" in deduped[0].signal_label


def test_dedupe_events_keeps_distinct_events_separate():
    now = datetime.now(UTC)
    items = [
        make_evidence("Funding news", "Acme raises $10M in Series A funding round", published_at=now),
        make_evidence("Leadership change", "Acme appoints a new CFO", category="executive", published_at=now),
    ]
    deduped = dedupe_events(items)
    assert len(deduped) == 2


def test_dedupe_events_keeps_events_outside_the_time_window_separate():
    now = datetime.now(UTC)
    items = [
        make_evidence("Funding news", "Acme raises $10M in Series A funding round", published_at=now),
        make_evidence(
            "Funding news", "Acme raises $10M in Series A funding round", published_at=now - timedelta(days=400)
        ),
    ]
    deduped = dedupe_events(items)
    # Same wording but ~13 months apart - two different funding events, not one story.
    assert len(deduped) == 2


def test_dedupe_events_boosts_confidence_when_corroborated():
    now = datetime.now(UTC)
    items = [
        make_evidence("Funding news", "Acme raises $10M in Series A funding round", source="TechCrunch", published_at=now, confidence=0.7),
        make_evidence("Funding news", "Acme raises $10M in Series A funding round", source="Forbes", published_at=now, confidence=0.7),
    ]
    deduped = dedupe_events(items)
    assert deduped[0].confidence > 0.7


def test_match_evidence_applies_dedup_so_n_sources_count_as_one_signal():
    now = datetime.now(UTC)
    items = [
        make_evidence(
            "Funding round", "Acme raises $10M in a funding round", source="TechCrunch", published_at=now
        ),
        make_evidence(
            "Funding round", "Acme raises $10M in a funding round this week", source="Forbes", published_at=now
        ),
        make_evidence(
            "Funding round", "Acme raises $10M in a funding round", source="Business Insider", published_at=now
        ),
    ]
    matched = match_evidence(items, ["funding round"])
    assert len(matched) == 1


def test_freshness_weighted_count_discounts_old_evidence():
    now = datetime.now(UTC)
    recent = [make_evidence("x", "y", published_at=now)]
    historical = [make_evidence("x", "y", published_at=now - timedelta(days=365 * 6))]
    assert freshness_weighted_count(recent) > freshness_weighted_count(historical)


def test_freshness_weighted_count_sums_weights_not_raw_count():
    now = datetime.now(UTC)
    items = [make_evidence("x", "y", published_at=now), make_evidence("x", "y", published_at=now - timedelta(days=365 * 6))]
    # One current (weight 1.0) + one historical (weight 0.05) = 1.05, not 2.
    assert freshness_weighted_count(items) < 1.1
    assert freshness_weighted_count(items) > 1.0
