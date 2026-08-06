import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models
from app.db.session import Base
from app.models.analysis_job import JobStatus
from app.repositories.job_repository import JobRepository
from app.tasks.analysis_tasks import execute_analysis_job


async def _make_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_execute_analysis_job_completes_and_links_company():
    session_factory = await _make_session_factory()

    async with session_factory() as session:
        job = await JobRepository(session).create(company_domain="acme.com", company_name=None)
        job_id = job.id

    await execute_analysis_job(job_id, "acme.com", None, session_factory=session_factory)

    async with session_factory() as session:
        job = await JobRepository(session).get(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.company_id is not None
        assert job.error_message is None


@pytest.mark.asyncio
async def test_execute_analysis_job_missing_job_is_a_noop():
    session_factory = await _make_session_factory()
    import uuid

    # Should log and return, not raise, when the job row doesn't exist.
    await execute_analysis_job(uuid.uuid4(), "acme.com", None, session_factory=session_factory)