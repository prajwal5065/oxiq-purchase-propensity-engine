import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models
from datetime import UTC, datetime, timedelta

from app.db.session import Base
from app.models.analysis_explanation import AnalysisExplanationRecord
from app.models.score import Score, ScoreType
from app.repositories.company_repository import CompanyRepository


async def _make_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


@pytest.mark.asyncio
async def test_list_with_latest_summary_joins_score_and_explanation():
    session = await _make_session()
    repo = CompanyRepository(session)

    company = await repo.get_or_create(domain="acme.com", name="Acme")
    await repo.add_scores(
        company, [Score(score_type=ScoreType.PURCHASE_PROPENSITY, value=85.0, confidence=0.9, reasons=[])]
    )
    await repo.add_explanation(
        company,
        AnalysisExplanationRecord(
            payload={
                "disqualification": {"final_decision": "qualified", "category": "not_disqualified"},
                "confidence_explanation": {"overall_confidence": 0.9},
                "evidence_coverage": {"coverage_percentage": 1.0},
            }
        ),
    )
    await repo.commit()

    rows = await repo.list_with_latest_summary()
    assert len(rows) == 1
    fetched_company, purchase_score, payload = rows[0]
    assert fetched_company.domain == "acme.com"
    assert purchase_score == 85.0
    assert payload["disqualification"]["final_decision"] == "qualified"
    await session.close()


@pytest.mark.asyncio
async def test_list_with_latest_summary_handles_unanalyzed_company():
    session = await _make_session()
    repo = CompanyRepository(session)
    await repo.get_or_create(domain="unanalyzed.com", name="Unanalyzed")
    await repo.commit()

    rows = await repo.list_with_latest_summary()
    _, purchase_score, payload = rows[0]
    assert purchase_score is None
    assert payload is None
    await session.close()


@pytest.mark.asyncio
async def test_list_with_latest_summary_uses_the_most_recent_explanation():
    session = await _make_session()
    repo = CompanyRepository(session)
    company = await repo.get_or_create(domain="acme.com", name="Acme")

    await repo.add_explanation(
        company,
        AnalysisExplanationRecord(
            payload={"disqualification": {"final_decision": "insufficient_data"}},
            created_at=datetime.now(UTC) - timedelta(minutes=5),
        ),
    )
    await repo.commit()
    await repo.add_explanation(
        company,
        AnalysisExplanationRecord(
            payload={"disqualification": {"final_decision": "qualified"}},
            created_at=datetime.now(UTC),
        ),
    )
    await repo.commit()

    rows = await repo.list_with_latest_summary()
    _, _, payload = rows[0]
    assert payload["disqualification"]["final_decision"] == "qualified"
    await session.close()


@pytest.mark.asyncio
async def test_list_all_latest_explanations_returns_every_company():
    session = await _make_session()
    repo = CompanyRepository(session)
    await repo.get_or_create(domain="a.com", name="A")
    await repo.get_or_create(domain="b.com", name="B")
    await repo.commit()

    rows = await repo.list_all_latest_explanations()
    assert len(rows) == 2
    await session.close()
