from datetime import UTC, datetime, timedelta

import pytest

from app.schemas.evidence import EvidenceItem
from app.scoring.time_decay import UNKNOWN_RECENCY_WEIGHT, decay_weight
from app.scoring.urgency_scorer import UrgencyScoringAgent


def make_evidence(label: str, excerpt: str, published_at=None, confidence: float = 0.9) -> EvidenceItem:
    return EvidenceItem(
        signal_label=label,
        excerpt=excerpt,
        source="Google News",
        confidence=confidence,
        published_at=published_at,
    )


def test_decay_weight_buckets():
    now = datetime(2026, 8, 6, tzinfo=UTC)
    assert decay_weight(now - timedelta(days=1), now=now) == 1.0
    assert decay_weight(now - timedelta(days=30), now=now) == 0.7
    assert decay_weight(now - timedelta(days=200), now=now) == 0.4
    assert decay_weight(now - timedelta(days=500), now=now) == 0.15
    # 2+ years old (e.g. a 2016-2019 style mention) - the "historical"
    # tier, weighted well below merely "stale" (1-2yr) evidence.
    assert decay_weight(now - timedelta(days=800), now=now) == 0.05


def test_decay_weight_unknown_recency():
    assert decay_weight(None) == UNKNOWN_RECENCY_WEIGHT


@pytest.mark.asyncio
async def test_urgency_scorer_weighs_recent_signal_higher_than_old():
    now = datetime.now(UTC)
    recent = [make_evidence("Funding round", "raised $10M in a funding round", published_at=now - timedelta(days=2))]
    old = [make_evidence("Funding round", "raised $10M in a funding round", published_at=now - timedelta(days=800))]

    recent_score = await UrgencyScoringAgent().score("acme.com", recent)
    old_score = await UrgencyScoringAgent().score("acme.com", old)

    assert recent_score.score > old_score.score


@pytest.mark.asyncio
async def test_urgency_scorer_unknown_date_is_moderate():
    evidence = [make_evidence("Funding round", "raised $10M in a funding round", published_at=None)]
    result = await UrgencyScoringAgent().score("acme.com", evidence)
    assert 0 < result.score < 100
