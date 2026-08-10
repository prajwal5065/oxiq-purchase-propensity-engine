"""Repository pattern for Company + related rows. Keeps SQLAlchemy query
code out of the service/API layers.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis_explanation import AnalysisExplanationRecord
from app.models.company import Company
from app.models.evidence import Evidence
from app.models.recommendation import Recommendation
from app.models.score import Score, ScoreType
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
                selectinload(Company.explanations),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, limit: int = 50, offset: int = 0, industry: str | None = None
    ) -> list[Company]:
        stmt = select(Company).order_by(Company.created_at.desc()).limit(limit).offset(offset)
        if industry:
            stmt = stmt.where(Company.industry == industry)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_with_latest_summary(
        self, limit: int = 50, offset: int = 0, industry: str | None = None
    ) -> list[tuple[Company, float | None, dict | None]]:
        """Company rows plus each one's latest purchase score and latest
        explanation payload, in a single query - what the dashboard's
        company list needs to show a decision badge per row without an
        N+1 fetch (or eager-loading every company's full scores/evidence/
        explanation history just to read one number off each)."""
        latest_score = (
            select(Score.value)
            .where(Score.company_id == Company.id, Score.score_type == ScoreType.PURCHASE_PROPENSITY)
            .order_by(Score.created_at.desc())
            .limit(1)
            .correlate(Company)
            .scalar_subquery()
        )
        latest_explanation_id = (
            select(AnalysisExplanationRecord.id)
            .where(AnalysisExplanationRecord.company_id == Company.id)
            .order_by(AnalysisExplanationRecord.created_at.desc())
            .limit(1)
            .correlate(Company)
            .scalar_subquery()
        )
        stmt = (
            select(Company, latest_score, AnalysisExplanationRecord.payload)
            .outerjoin(AnalysisExplanationRecord, AnalysisExplanationRecord.id == latest_explanation_id)
            .order_by(Company.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if industry:
            stmt = stmt.where(Company.industry == industry)
        result = await self.session.execute(stmt)
        return [tuple(row) for row in result.all()]

    async def list_all_latest_explanations(self) -> list[tuple[float | None, dict | None]]:
        """Every company's latest purchase score + explanation payload,
        unpaginated - the raw material for the portfolio-wide dashboard
        summary. Kept separate from list_with_latest_summary because the
        summary endpoint needs every company, not one page of them."""
        latest_score = (
            select(Score.value)
            .where(Score.company_id == Company.id, Score.score_type == ScoreType.PURCHASE_PROPENSITY)
            .order_by(Score.created_at.desc())
            .limit(1)
            .correlate(Company)
            .scalar_subquery()
        )
        latest_explanation_id = (
            select(AnalysisExplanationRecord.id)
            .where(AnalysisExplanationRecord.company_id == Company.id)
            .order_by(AnalysisExplanationRecord.created_at.desc())
            .limit(1)
            .correlate(Company)
            .scalar_subquery()
        )
        stmt = select(latest_score, AnalysisExplanationRecord.payload).select_from(Company).outerjoin(
            AnalysisExplanationRecord, AnalysisExplanationRecord.id == latest_explanation_id
        )
        result = await self.session.execute(stmt)
        return [tuple(row) for row in result.all()]

    async def count_all(self, industry: str | None = None) -> int:
        stmt = select(func.count()).select_from(Company)
        if industry:
            stmt = stmt.where(Company.industry == industry)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

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

    async def add_recommendation(self, company: Company, recommendation: Recommendation) -> None:
        recommendation.company_id = company.id
        self.session.add(recommendation)

    async def add_explanation(self, company: Company, explanation: AnalysisExplanationRecord) -> None:
        explanation.company_id = company.id
        self.session.add(explanation)

    async def commit(self) -> None:
        await self.session.commit()
