from datetime import UTC, datetime, timedelta

import pytest

from app.schemas.evidence import EvidenceItem
from app.scoring.capacity_scorer import CapacityScoringAgent
from app.scoring.need_scorer import NeedScoringAgent
from app.scoring.urgency_scorer import UrgencyScoringAgent


def make_evidence(label: str, excerpt: str, confidence: float = 0.9, published_at=None) -> EvidenceItem:
    return EvidenceItem(
        signal_label=label, excerpt=excerpt, source="Careers Page", confidence=confidence, published_at=published_at
    )


@pytest.mark.asyncio
async def test_need_scorer_matches_relevant_evidence():
    evidence = [
        make_evidence("Hiring AI Engineers", "We are hiring an AI engineer to automate manual workflow"),
        make_evidence("Unrelated", "We sell furniture"),
    ]
    result = await NeedScoringAgent().score("acme.com", evidence)
    assert result.score > 0
    assert result.confidence > 0
    assert len(result.reasons) == 1


@pytest.mark.asyncio
async def test_urgency_scorer_zero_when_no_matches():
    evidence = [make_evidence("Unrelated", "We sell furniture")]
    result = await UrgencyScoringAgent().score("acme.com", evidence)
    assert result.score == 0
    assert result.confidence == 0
    assert result.reasons == []


@pytest.mark.asyncio
async def test_capacity_scorer_saturates_at_max_expected():
    now = datetime.now(UTC)
    evidence = [
        make_evidence("Headcount", "The company has 500 employees", published_at=now),
        make_evidence("Revenue", "Annual recurring revenue of $50M", published_at=now),
        make_evidence("Customers", "Serves several Fortune 500 enterprise customer accounts", published_at=now),
        make_evidence("Funding", "Raised $30M in funding", published_at=now),
        make_evidence("Extra", "Valuation reached $1B", published_at=now),
    ]
    result = await CapacityScoringAgent().score("acme.com", evidence)
    assert result.score == 100.0


@pytest.mark.asyncio
async def test_capacity_scorer_confidence_is_lower_for_search_derived_evidence_than_structured():
    """Item-level extraction confidence being 0.9 for both should NOT mean
    equal pillar confidence: a 'search' collector item is a weaker source
    than a 'github'/'tech' collector item, and the composite should reflect
    that (see EvidenceConfidenceEngine, now wired into _confidence_from_evidence)."""
    now = datetime.now(UTC)
    search_item = EvidenceItem(
        signal_label="Headcount",
        excerpt="The company has 500 employees",
        source="Search",
        collector="search",
        confidence=0.9,
        published_at=now,
    )
    github_item = EvidenceItem(
        signal_label="Headcount",
        excerpt="The company has 500 employees",
        source="GitHub",
        collector="github",
        confidence=0.9,
        published_at=now,
    )
    search_result = await CapacityScoringAgent().score("acme.com", [search_item])
    github_result = await CapacityScoringAgent().score("acme.com", [github_item])

    assert github_result.confidence > search_result.confidence


@pytest.mark.asyncio
async def test_capacity_scorer_confidence_is_lower_for_historical_evidence():
    recent_item = EvidenceItem(
        signal_label="Headcount",
        excerpt="The company has 500 employees",
        source="Search",
        collector="search",
        confidence=0.9,
        published_at=datetime.now(UTC),
    )
    historical_item = EvidenceItem(
        signal_label="Headcount",
        excerpt="The company has 500 employees",
        source="Search",
        collector="search",
        confidence=0.9,
        published_at=datetime.now(UTC) - timedelta(days=365 * 6),
    )
    recent_result = await CapacityScoringAgent().score("acme.com", [recent_item])
    historical_result = await CapacityScoringAgent().score("acme.com", [historical_item])

    assert recent_result.confidence > historical_result.confidence
