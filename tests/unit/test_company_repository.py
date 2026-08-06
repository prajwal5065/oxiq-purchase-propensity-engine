import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models
from app.db.session import Base
from app.repositories.company_repository import CompanyRepository


async def _make_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


@pytest.mark.asyncio
async def test_list_all_and_count_respect_industry_filter():
    session = await _make_session()
    repo = CompanyRepository(session)

    saas_co = await repo.get_or_create(domain="saas.com", name="SaaS Co")
    saas_co.industry = "SaaS"
    fintech_co = await repo.get_or_create(domain="fintech.com", name="Fintech Co")
    fintech_co.industry = "Fintech"
    await repo.commit()

    saas_only = await repo.list_all(industry="SaaS")
    assert [c.domain for c in saas_only] == ["saas.com"]

    total_all = await repo.count_all()
    total_saas = await repo.count_all(industry="SaaS")
    assert total_all == 2
    assert total_saas == 1
    await session.close()


@pytest.mark.asyncio
async def test_list_all_respects_limit_and_offset():
    session = await _make_session()
    repo = CompanyRepository(session)

    for i in range(5):
        await repo.get_or_create(domain=f"company{i}.com", name=f"Company {i}")
    await repo.commit()

    page = await repo.list_all(limit=2, offset=1)
    assert len(page) == 2
    total = await repo.count_all()
    assert total == 5
    await session.close()
