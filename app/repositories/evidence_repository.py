"""Repository for the Evidence Store.

Split out from CompanyRepository so evidence persistence and querying has
its own home, per the architecture's "Evidence Store" stage: scorers and
the dashboard should be able to ask this repository for evidence grouped by
company/category/pillar without knowing anything about how it's collected
or normalized. CompanyRepository.add_evidence still exists for backward
compatibility with any other caller, but the orchestrator now goes through
here.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceItem


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add_batch(self, company: Company, items: list[EvidenceItem]) -> list[Evidence]:
        """Convert normalized EvidenceItems to ORM rows and stage them on the
        session (does not commit - caller controls the transaction boundary,
        matching CompanyRepository's existing pattern)."""
        models = [self._to_model(company.id, item) for item in items]
        for model in models:
            self.session.add(model)
        return models

    async def list_by_company(self, company_id: uuid.UUID) -> list[Evidence]:
        stmt = select(Evidence).where(Evidence.company_id == company_id).order_by(Evidence.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_category(self, company_id: uuid.UUID, category: str) -> list[Evidence]:
        stmt = select(Evidence).where(Evidence.company_id == company_id, Evidence.category == category)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_pillar(self, company_id: uuid.UUID, pillar: str) -> list[Evidence]:
        stmt = select(Evidence).where(Evidence.company_id == company_id, Evidence.pillar == pillar)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_collector(self, company_id: uuid.UUID) -> dict[str, int]:
        """Evidence count grouped by collector - the basis for the "Sources
        Checked" coverage view (Stage 7), computed straight from the DB
        rather than recomputed from raw collector results every time."""
        stmt = (
            select(Evidence.collector, func.count())
            .where(Evidence.company_id == company_id)
            .group_by(Evidence.collector)
        )
        result = await self.session.execute(stmt)
        return {collector or "unknown": count for collector, count in result.all()}

    @staticmethod
    def _to_model(company_id: uuid.UUID, item: EvidenceItem) -> Evidence:
        return Evidence(
            id=item.id,
            company_id=company_id,
            signal_label=item.signal_label,
            excerpt=item.excerpt,
            source=item.source,
            url=str(item.url) if item.url else None,
            confidence=item.confidence,
            category=item.category,
            collector=item.collector,
            pillar=item.pillar,
            published_at=item.published_at,
            technology_name=item.technology_name,
            technology_provider=item.technology_provider,
            job_title=item.job_title,
            job_department=item.job_department,
            job_location=item.job_location,
            job_ats_provider=item.job_ats_provider,
            job_posting_date=item.job_posting_date,
        )
