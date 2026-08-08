import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models
from app.db.session import Base
from app.models.analysis_job import JobStatus
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.schemas.explanation import AnalysisExplanation
from app.tasks.analysis_tasks import execute_analysis_job


async def _make_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_full_analysis_persists_a_retrievable_explanation():
    """End-to-end: running an analysis (in stub mode, no live collectors)
    should still produce and persist a full AnalysisExplanation - the
    dossier page must always have something to show, even when every
    collector came back empty."""
    session_factory = await _make_session_factory()

    async with session_factory() as session:
        job = await JobRepository(session).create(company_domain="acme.com", company_name=None)
        job_id = job.id

    await execute_analysis_job(job_id, "acme.com", None, session_factory=session_factory)

    async with session_factory() as session:
        job = await JobRepository(session).get(job_id)
        assert job.status == JobStatus.COMPLETED

        company_repo = CompanyRepository(session)
        company = await company_repo.get_by_id(job.company_id)
        assert company is not None
        assert len(company.explanations) == 1

        explanation = AnalysisExplanation.model_validate(company.explanations[0].payload)

        # In stub mode every collector is NOT_CONFIGURED, so this must never
        # be reported as a business conclusion about the company.
        assert explanation.disqualification.final_decision in ("insufficient_data", "qualified")
        assert explanation.disqualification.final_decision != "disqualified"
        assert explanation.headline in (
            "WHY WE CANNOT RECOMMEND THIS COMPANY",
            "WHY THIS COMPANY SCORED HIGH",
            "WHY THIS COMPANY SCORED LOW",
        )
        assert explanation.evidence_coverage.sources_discovered == 5
