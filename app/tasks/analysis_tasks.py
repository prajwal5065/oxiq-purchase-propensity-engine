"""Celery task that runs the full analysis pipeline in the background.

The Celery task itself is a thin sync wrapper (`run_analysis_task`) around
`execute_analysis_job`, which does the real (async) work and takes an
optional session factory so it can be unit-tested against SQLite without a
live Postgres or a running Celery worker.
"""
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.services.analysis_orchestrator import AnalysisOrchestrator

logger = get_logger(__name__)


async def execute_analysis_job(
    job_id: uuid.UUID,
    company_domain: str,
    company_name: str | None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Run one analysis end-to-end and update the AnalysisJob row throughout.
    Never raises - failures are recorded on the job row instead, since this
    runs unattended in a worker process."""
    factory = session_factory or AsyncSessionLocal

    async with factory() as session:
        job_repo = JobRepository(session)
        job = await job_repo.get(job_id)
        if job is None:
            logger.error("analysis_task.job_not_found", job_id=str(job_id))
            return

        await job_repo.mark_running(job)

        try:
            company_repo = CompanyRepository(session)
            orchestrator = AnalysisOrchestrator(company_repo)
            await orchestrator.analyze(company_domain=company_domain, company_name=company_name)

            company = await company_repo.get_by_domain(company_domain)
            if company is None:
                raise RuntimeError("Company was not persisted during analysis")

            await job_repo.mark_completed(job, company_id=company.id)
            logger.info("analysis_task.completed", job_id=str(job_id), domain=company_domain)
        except Exception as exc:  # noqa: BLE001 - always land the job in a terminal state
            logger.error("analysis_task.failed", job_id=str(job_id), domain=company_domain, error=str(exc))
            await job_repo.mark_failed(job, error_message=str(exc))


@celery_app.task(name="run_analysis")
def run_analysis_task(job_id: str, company_domain: str, company_name: str | None = None) -> None:
    """Run the async pipeline in a dedicated thread so it always gets a clean
    event loop — even when Celery is in ALWAYS_EAGER mode and the task is
    called from within FastAPI's running event loop."""
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            asyncio.run,
            execute_analysis_job(uuid.UUID(job_id), company_domain, company_name),
        )
        future.result()  # block until done (noop overhead in a real worker)
