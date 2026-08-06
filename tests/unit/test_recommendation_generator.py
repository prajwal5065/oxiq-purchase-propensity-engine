import pytest

from app.recommendation.generator import RecommendationGenerator
from app.schemas.score import PurchaseScoreResult


@pytest.mark.asyncio
async def test_high_score_gets_high_priority():
    result = PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=[],
        purchase_score=85.0,
        confidence=0.8,
        evidence_summary=["Hiring AI engineers: we are hiring"],
    )
    rec = await RecommendationGenerator().generate("acme.com", result, evidence=[])
    assert rec.contact_priority == "high"
    assert "acme.com" in rec.executive_summary
    assert rec.solution_match is None


@pytest.mark.asyncio
async def test_disqualified_company_gets_low_priority_and_reason_surfaced():
    result = PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=[],
        purchase_score=0.0,
        confidence=0.0,
        evidence_summary=[],
        disqualified=True,
        disqualified_reason="No pillar produced any matched evidence",
    )
    rec = await RecommendationGenerator().generate("acme.com", result, evidence=[])
    assert rec.contact_priority == "low"
    assert "No pillar produced any matched evidence" in rec.executive_summary


@pytest.mark.asyncio
async def test_low_score_gets_low_priority():
    result = PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=[],
        purchase_score=20.0,
        confidence=0.3,
        evidence_summary=[],
    )
    rec = await RecommendationGenerator().generate("acme.com", result, evidence=[])
    assert rec.contact_priority == "low"
