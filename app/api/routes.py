"""API routes: POST /analyze, GET /company/{id}, GET /companies, GET /scores/{id}."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.company_repository import CompanyRepository
from app.schemas.api import AnalyzeRequest, AnalyzeResponse, CompanySummary
from app.schemas.score import PillarScore
from app.services.analysis_orchestrator import AnalysisOrchestrator

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_company(payload: AnalyzeRequest, db: AsyncSession = Depends(get_db)) -> AnalyzeResponse:
    repo = CompanyRepository(db)
    orchestrator = AnalysisOrchestrator(repo)
    pillar_scores = await orchestrator.analyze(company_domain=payload.domain, company_name=payload.name)
    company = await repo.get_by_domain(payload.domain)
    if company is None:
        raise HTTPException(status_code=500, detail="Company was not persisted during analysis")
    return AnalyzeResponse(company_id=company.id, domain=company.domain, pillar_scores=pillar_scores)


@router.get("/company/{company_id}", response_model=CompanySummary)
async def get_company(company_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> CompanySummary:
    repo = CompanyRepository(db)
    company = await repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanySummary.model_validate(company)


@router.get("/companies", response_model=list[CompanySummary])
async def list_companies(
    limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)
) -> list[CompanySummary]:
    repo = CompanyRepository(db)
    companies = await repo.list_all(limit=limit, offset=offset)
    return [CompanySummary.model_validate(c) for c in companies]


@router.get("/scores/{company_id}", response_model=list[PillarScore])
async def get_scores(company_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[PillarScore]:
    repo = CompanyRepository(db)
    company = await repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return [
        PillarScore(
            score_type=s.score_type,
            score=s.value,
            confidence=s.confidence,
            reasons=s.reasons,
        )
        for s in company.scores
    ]
