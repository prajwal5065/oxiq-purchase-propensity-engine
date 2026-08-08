"""API routes.

POST /analyze         - enqueue a background analysis job, return immediately
GET  /jobs/{job_id}    - poll job status
GET  /company/{id}     - company summary
GET  /companies        - paginated company list, optional industry filter
GET  /scores/{id}      - a company's pillar + purchase-propensity scores
GET  /company/{id}/recommendation - latest recommendation for a company
GET  /company/{id}/explanation    - evidence coverage, confidence, pillar
                                     attribution, and disqualification
                                     reasoning behind a company's score
GET  /company/{id}/evidence       - full evidence records (source, url,
                                     date, confidence, collector, category,
                                     pillar) for the dossier's evidence cards
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.schemas.api import (
    AnalyzeJobAccepted,
    AnalyzeRequest,
    CompanyListResponse,
    CompanySummary,
    JobStatusResponse,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.explanation import AnalysisExplanation
from app.schemas.recommendation import RecommendationResult
from app.schemas.score import PillarScore
from app.tasks.analysis_tasks import run_analysis_task

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeJobAccepted, status_code=202)
async def analyze_company(
    payload: AnalyzeRequest, db: AsyncSession = Depends(get_db)
) -> AnalyzeJobAccepted:
    job_repo = JobRepository(db)
    job = await job_repo.create(company_domain=payload.domain, company_name=payload.name)

    run_analysis_task.delay(job_id=str(job.id), company_domain=payload.domain, company_name=payload.name)

    return AnalyzeJobAccepted(
        job_id=job.id, status=job.status, status_url=f"/jobs/{job.id}"
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> JobStatusResponse:
    job_repo = JobRepository(db)
    job = await job_repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        company_domain=job.company_domain,
        company_id=job.company_id,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/company/{company_id}", response_model=CompanySummary)
async def get_company(company_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> CompanySummary:
    repo = CompanyRepository(db)
    company = await repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanySummary.model_validate(company)


@router.get("/companies", response_model=CompanyListResponse)
async def list_companies(
    limit: int = 50,
    offset: int = 0,
    industry: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> CompanyListResponse:
    repo = CompanyRepository(db)
    companies = await repo.list_all(limit=limit, offset=offset, industry=industry)
    total = await repo.count_all(industry=industry)
    return CompanyListResponse(
        items=[CompanySummary.model_validate(c) for c in companies],
        total=total,
        limit=limit,
        offset=offset,
    )


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


@router.get("/company/{company_id}/recommendation", response_model=RecommendationResult)
async def get_recommendation(
    company_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> RecommendationResult:
    repo = CompanyRepository(db)
    company = await repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if not company.recommendations:
        raise HTTPException(status_code=404, detail="No recommendation generated yet for this company")

    latest = max(company.recommendations, key=lambda r: r.created_at)
    return RecommendationResult(
        executive_summary=latest.executive_summary,
        fit_reasons=latest.fit_reasons,
        top_buying_signals=latest.top_buying_signals,
        top_risks=latest.top_risks,
        suggested_approach=latest.suggested_approach,
        contact_priority=latest.contact_priority,
        solution_match=latest.solution_match,
    )


@router.get("/company/{company_id}/explanation", response_model=AnalysisExplanation)
async def get_explanation(
    company_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> AnalysisExplanation:
    """The evidence-first "why" behind a company's score: coverage,
    confidence factors, per-pillar attribution, and (when applicable) a
    structured disqualification explanation - never a bare number."""
    repo = CompanyRepository(db)
    company = await repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if not company.explanations:
        raise HTTPException(status_code=404, detail="No analysis explanation generated yet for this company")

    latest = max(company.explanations, key=lambda e: e.created_at)
    return AnalysisExplanation.model_validate(latest.payload)


@router.get("/company/{company_id}/evidence", response_model=list[EvidenceRecord])
async def get_evidence(company_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[EvidenceRecord]:
    """Full evidence records (source, url, date, confidence, collector,
    category, pillar, excerpt) - what the frontend's evidence cards render,
    as opposed to /scores which only carries the flattened reason strings."""
    repo = CompanyRepository(db)
    company = await repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return [EvidenceRecord.model_validate(item) for item in company.evidence_items]
