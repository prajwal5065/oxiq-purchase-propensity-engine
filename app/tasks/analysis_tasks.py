"""Celery task that runs the full analysis pipeline in the background.

The Celery task itself is a thin sync wrapper (`run_analysis_task`) around
`execute_analysis_job`, which does the real (async) work and takes an
optional session factory so it can be unit-tested against SQLite without a
live Postgres or a running Celery worker.

Cross-loop safety
-----------------
When Celery runs in ALWAYS_EAGER mode the task executes inline inside
FastAPI's own event loop thread.  We escape by running the async work in a
dedicated ThreadPoolExecutor thread that calls asyncio.run() — giving us a
completely new, independent event loop.

The module-level engine in app.db.session is bound to FastAPI's event loop.
If a task thread reuses it, asyncpg raises:
    RuntimeError: ... got Future ... attached to a different loop

Fix: `run_analysis_task` builds a *fresh* engine (NullPool — no connection
caching) inside the worker thread and disposes it when the job finishes.
NullPool means every DB call opens and closes a real connection, which is
fine for background jobs that run once per request.
"""
import asyncio
import concurrent.futures
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.db.session import make_session_factory
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
    factory = session_factory

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


def _run_in_fresh_loop(job_id: uuid.UUID, company_domain: str, company_name: str | None) -> None:
    """Entry point for the worker thread.

    Called from a ThreadPoolExecutor so it owns the thread and can safely
    call asyncio.run() to create a brand-new event loop.  A fresh NullPool
    engine is created here — inside that loop — so every asyncpg connection
    is born in the correct loop and never crosses a loop boundary.
    """
    session_factory, task_engine = make_session_factory()
    try:
        asyncio.run(
            execute_analysis_job(job_id, company_domain, company_name, session_factory)
        )
    finally:
        # Dispose synchronously; the loop is still alive inside asyncio.run
        # at this point so we use the sync dispose path.
        task_engine.sync_engine.dispose()


@celery_app.task(name="run_analysis")
def run_analysis_task(job_id: str, company_domain: str, company_name: str | None = None) -> None:
    """Run the async pipeline in a dedicated thread so it always gets a clean
    event loop — even when Celery is in ALWAYS_EAGER mode and the task is
    called from within FastAPI's running event loop."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run_in_fresh_loop, uuid.UUID(job_id), company_domain, company_name)
        future.result()  # re-raises any exception from the worker thread

