import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models
from app.db.session import Base
from app.repositories.company_repository import CompanyRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.evidence import EvidenceItem


async def _make_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


def make_item(category: str, collector: str, confidence: float = 0.8) -> EvidenceItem:
    return EvidenceItem(
        signal_label="x", excerpt="y", source="Careers Page", confidence=confidence,
        category=category, collector=collector,
    )


@pytest.mark.asyncio
async def test_add_batch_and_list_by_company():
    session = await _make_session()
    company_repo = CompanyRepository(session)
    evidence_repo = EvidenceRepository(session)

    company = await company_repo.get_or_create(domain="acme.com", name="Acme")
    evidence_repo.add_batch(company, [make_item("hiring", "website"), make_item("funding", "news")])
    await company_repo.commit()

    rows = await evidence_repo.list_by_company(company.id)
    assert len(rows) == 2
    await session.close()


@pytest.mark.asyncio
async def test_list_by_category_filters_correctly():
    session = await _make_session()
    company_repo = CompanyRepository(session)
    evidence_repo = EvidenceRepository(session)

    company = await company_repo.get_or_create(domain="acme.com", name="Acme")
    evidence_repo.add_batch(
        company, [make_item("hiring", "website"), make_item("hiring", "website"), make_item("funding", "news")]
    )
    await company_repo.commit()

    hiring_rows = await evidence_repo.list_by_category(company.id, "hiring")
    assert len(hiring_rows) == 2
    await session.close()


@pytest.mark.asyncio
async def test_count_by_collector_groups_correctly():
    session = await _make_session()
    company_repo = CompanyRepository(session)
    evidence_repo = EvidenceRepository(session)

    company = await company_repo.get_or_create(domain="acme.com", name="Acme")
    evidence_repo.add_batch(
        company,
        [make_item("hiring", "website"), make_item("funding", "news"), make_item("expansion", "website")],
    )
    await company_repo.commit()

    counts = await evidence_repo.count_by_collector(company.id)
    assert counts["website"] == 2
    assert counts["news"] == 1
    await session.close()
