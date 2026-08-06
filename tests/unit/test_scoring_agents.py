import pytest

from app.schemas.evidence import EvidenceItem
from app.scoring.capacity_scorer import CapacityScoringAgent
from app.scoring.need_scorer import NeedScoringAgent
from app.scoring.urgency_scorer import UrgencyScoringAgent


def make_evidence(label: str, excerpt: str, confidence: float = 0.9) -> EvidenceItem:
    return EvidenceItem(signal_label=label, excerpt=excerpt, source="Careers Page", confidence=confidence)


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
    evidence = [
        make_evidence("Headcount", "The company has 500 employees"),
        make_evidence("Revenue", "Annual recurring revenue of $50M"),
        make_evidence("Customers", "Serves several Fortune 500 enterprise customer accounts"),
        make_evidence("Funding", "Raised $30M in funding"),
        make_evidence("Extra", "Valuation reached $1B"),
    ]
    result = await CapacityScoringAgent().score("acme.com", evidence)
    assert result.score == 100.0
