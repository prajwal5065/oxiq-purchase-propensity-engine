"""Repository pattern for Company + related rows. Keeps SQLAlchemy query
code out of the service/API layers.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.evidence import Evidence
from app.models.score import Score
from app.models.signal import Signal


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_domain(self, domain: str) -> Company | None:
        stmt = select(Company).where(Company.domain == domain)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, company_id) -> Company | None:  # noqa: ANN001 - uuid.UUID
        stmt = (
            select(Company)
            .where(Company.id == company_id)
            .options(
                selectinload(Company.scores),
                selectinload(Company.evidence_items),
                selectinload(Company.recommendations),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[Company]:
        stmt = select(Company).order_by(Company.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_or_create(self, domain: str, name: str) -> Company:
        existing = await self.get_by_domain(domain)
        if existing:
            return existing
        company = Company(domain=domain, name=name)
        self.session.add(company)
        await self.session.flush()
        return company

    async def add_signals(self, company: Company, signals: list[Signal]) -> None:
        for signal in signals:
            signal.company_id = company.id
            self.session.add(signal)

    async def add_evidence(self, company: Company, evidence: list[Evidence]) -> None:
        for item in evidence:
            item.company_id = company.id
            self.session.add(item)

    async def add_scores(self, company: Company, scores: list[Score]) -> None:
        for score in scores:
            score.company_id = company.id
            self.session.add(score)

    async def commit(self) -> None:
        await self.session.commit()
