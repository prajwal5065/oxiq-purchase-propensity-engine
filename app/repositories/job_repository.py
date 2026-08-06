"""Repository for AnalysisJob - the async job-tracking row."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_job import AnalysisJob, JobStatus


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, company_domain: str, company_name: str | None) -> AnalysisJob:
        job = AnalysisJob(company_domain=company_domain, company_name=company_name, status=JobStatus.PENDING)
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get(self, job_id: uuid.UUID) -> AnalysisJob | None:
        stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_running(self, job: AnalysisJob) -> None:
        job.status = JobStatus.RUNNING
        await self.session.commit()

    async def mark_completed(self, job: AnalysisJob, company_id: uuid.UUID) -> None:
        job.status = JobStatus.COMPLETED
        job.company_id = company_id
        await self.session.commit()

    async def mark_failed(self, job: AnalysisJob, error_message: str) -> None:
        job.status = JobStatus.FAILED
        job.error_message = error_message
        await self.session.commit()
