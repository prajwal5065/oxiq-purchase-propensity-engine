from datetime import UTC, datetime, timedelta

from app.decision.evidence_confidence import EvidenceConfidenceEngine
from app.schemas.evidence import EvidenceItem


def make_evidence(confidence=0.8, collector="github", published_at=None):
    return EvidenceItem(
        signal_label="Hiring AI Engineers",
        excerpt="we are hiring",
        source="Careers Page",
        confidence=confidence,
        collector=collector,
        published_at=published_at,
    )


def test_composite_confidence_is_bounded_0_to_1():
    item = make_evidence(confidence=1.0, collector="github", published_at=datetime.now(UTC))
    score = EvidenceConfidenceEngine().score(item)
    assert 0.0 <= score.composite_confidence <= 1.0


def test_high_reliability_source_scores_higher_than_low_reliability_at_equal_confidence():
    now = datetime.now(UTC)
    github_item = make_evidence(confidence=0.7, collector="github", published_at=now)
    search_item = make_evidence(confidence=0.7, collector="search", published_at=now)

    engine = EvidenceConfidenceEngine()
    github_score = engine.score(github_item)
    search_score = engine.score(search_item)

    assert github_score.composite_confidence > search_score.composite_confidence


def test_fresher_evidence_scores_higher_than_stale_evidence_at_equal_confidence_and_source():
    now = datetime.now(UTC)
    fresh_item = make_evidence(confidence=0.7, collector="news", published_at=now - timedelta(days=1))
    stale_item = make_evidence(confidence=0.7, collector="news", published_at=now - timedelta(days=800))

    engine = EvidenceConfidenceEngine()
    fresh_score = engine.score(fresh_item)
    stale_score = engine.score(stale_item)

    assert fresh_score.composite_confidence > stale_score.composite_confidence


def test_score_carries_evidence_identity_for_traceability():
    item = make_evidence()
    score = EvidenceConfidenceEngine().score(item)

    assert score.evidence_id == item.id
    assert score.label == item.signal_label
    assert score.source == item.source
    assert score.collector == item.collector


def test_score_batch_sorts_descending_by_composite_confidence():
    now = datetime.now(UTC)
    low = make_evidence(confidence=0.2, collector="search", published_at=now - timedelta(days=800))
    high = make_evidence(confidence=0.95, collector="github", published_at=now)

    results = EvidenceConfidenceEngine().score_batch([low, high])

    assert results[0].evidence_id == high.id
    assert results[1].evidence_id == low.id


def test_score_batch_empty_list_returns_empty_list():
    assert EvidenceConfidenceEngine().score_batch([]) == []
