"""End-to-end proof that the structured Technology and Jobs fields survive
the complete pipeline:

    RawSignal (TechCollector/JobsCollector)
    -> EvidenceItem (simulated extraction + EvidenceNormalizer)
    -> Evidence ORM row (EvidenceRepository persistence)
    -> EvidenceRecord (the API's response schema)

The "simulated extraction" step stands in for the Evidence Extractor's LLM
call (app/extraction/evidence_extractor.py) - same convention as
tests/integration/test_jobs_to_decision.py - so this test exercises every
real, non-LLM stage of the pipeline without requiring live API credentials.
"""
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.collectors.jobs_collector import JobsCollector
from app.collectors.tech_collector import TechCollector
from app.db.session import Base
from app.repositories.company_repository import CompanyRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.evidence import EvidenceItem, EvidenceRecord
from app.services.evidence_normalizer import EvidenceNormalizer

BUILTWITH_API_URL = "https://api.builtwith.com/v23/api.json"

BUILTWITH_RESPONSE = {
    "Results": [
        {
            "Result": {
                "Paths": [
                    {
                        "Technologies": [
                            {"Name": "React", "Tag": "javascript-frameworks"},
                            {"Name": "AWS", "Tag": "hosting"},
                        ]
                    }
                ]
            }
        }
    ]
}

GREENHOUSE_RESPONSE = {
    "jobs": [
        {
            "id": 1,
            "title": "Machine Learning Engineer",
            "updated_at": None,  # set per-test
            "location": {"name": "Remote"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
            "content": "<p>Acme is hiring machine learning engineers to build production models.</p>",
            "departments": [{"name": "AI"}],
        }
    ]
}


async def _make_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, expire_on_commit=False)


def _simulate_tech_extraction(raw_signals) -> list[EvidenceItem]:
    """Stand-in for the LLM extraction step for technology signals: the url
    is carried through verbatim, exactly as the extraction prompt requires
    of a real LLM call, which is what EvidenceNormalizer's URL match relies
    on."""
    return [
        EvidenceItem(
            signal_label=f"Uses {signal.payload['technology']}",
            excerpt=f"The site is built with {signal.payload['technology']}",
            source=signal.payload["provider"].title(),
            confidence=0.85,
            url=signal.url,
        )
        for signal in raw_signals
    ]


def _simulate_jobs_extraction(raw_signals) -> list[EvidenceItem]:
    items = []
    for signal in raw_signals:
        payload = signal.payload
        published_at = datetime.fromisoformat(payload["posted_at"]) if payload.get("posted_at") else None
        items.append(
            EvidenceItem(
                signal_label=payload["title"],
                excerpt=payload["description_snippet"] or payload["title"],
                source=f"{payload['provider'].title()} Job Posting",
                confidence=0.85,
                url=signal.url,
                published_at=published_at,
            )
        )
    return items


@pytest.mark.asyncio
@respx.mock
async def test_technology_fields_flow_from_collector_to_api_schema(monkeypatch):
    """RawSignal -> EvidenceItem -> Evidence (persisted) -> EvidenceRecord,
    proving technology_name/technology_provider survive every hop, while the
    original excerpt/signal_label text is preserved unchanged."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_LIVE_TECH_DETECTION", "true")
    monkeypatch.setenv("BUILTWITH_API_KEY", "test_key")

    respx.get(BUILTWITH_API_URL).mock(return_value=httpx.Response(200, json=BUILTWITH_RESPONSE))

    # Stage 1: TechCollector -> RawSignal (BuiltWith primary)
    collector_result = await TechCollector().collect("acme.com")
    assert len(collector_result.signals) == 2
    react_signal = next(s for s in collector_result.signals if s.payload["technology"] == "React")
    assert react_signal.payload["provider"] == "builtwith"

    # Stage 2: simulated extraction -> EvidenceItem (real LLM call substituted)
    extracted_items = _simulate_tech_extraction(collector_result.signals)

    # Stage 3: EvidenceNormalizer -> structured fields attached via URL match
    normalized = EvidenceNormalizer().normalize(raw_signals=collector_result.signals, items=extracted_items)
    react_item = next(i for i in normalized if i.technology_name == "React")
    assert react_item.technology_provider == "builtwith"
    assert react_item.collector == "tech"
    # Original text fields untouched.
    assert react_item.excerpt == "The site is built with React"

    # Stage 4: persist via EvidenceRepository, then read back
    session_factory = await _make_session_factory()
    async with session_factory() as session:
        company_repo = CompanyRepository(session)
        evidence_repo = EvidenceRepository(session)
        company = await company_repo.get_or_create(domain="acme.com", name="Acme")
        evidence_repo.add_batch(company, normalized)
        await company_repo.commit()

    async with session_factory() as session:
        company = await CompanyRepository(session).get_or_create(domain="acme.com", name="Acme")
        rows = await EvidenceRepository(session).list_by_company(company.id)

    persisted_react = next(r for r in rows if r.technology_name == "React")
    assert persisted_react.technology_provider == "builtwith"
    assert persisted_react.excerpt == "The site is built with React"

    # Stage 5: the API's response schema (what /company/{id}/evidence returns)
    record = EvidenceRecord.model_validate(persisted_react)
    assert record.technology_name == "React"
    assert record.technology_provider == "builtwith"
    assert record.excerpt == "The site is built with React"
    # Jobs fields must remain null on technology evidence.
    assert record.job_title is None

    get_settings.cache_clear()
    monkeypatch.delenv("ENABLE_LIVE_TECH_DETECTION", raising=False)
    monkeypatch.delenv("BUILTWITH_API_KEY", raising=False)


@pytest.mark.asyncio
@respx.mock
async def test_job_fields_flow_from_collector_to_api_schema(monkeypatch):
    """RawSignal -> EvidenceItem -> Evidence (persisted) -> EvidenceRecord,
    proving job_title/job_department/job_location/job_ats_provider/
    job_posting_date survive every hop."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_LIVE_JOBS", "true")

    now = datetime.now(UTC)
    response_body = GREENHOUSE_RESPONSE.copy()
    response_body["jobs"][0]["updated_at"] = (now - timedelta(days=2)).isoformat()

    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
        return_value=httpx.Response(200, json=response_body)
    )
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(404))

    # Stage 1: JobsCollector -> RawSignal
    collector_result = await JobsCollector().collect("acme.com")
    assert len(collector_result.signals) == 1

    # Stage 2: simulated extraction -> EvidenceItem
    extracted_items = _simulate_jobs_extraction(collector_result.signals)

    # Stage 3: EvidenceNormalizer -> structured fields attached via URL match
    normalized = EvidenceNormalizer().normalize(raw_signals=collector_result.signals, items=extracted_items)
    job_item = normalized[0]
    assert job_item.job_title == "Machine Learning Engineer"
    assert job_item.job_department == "AI"
    assert job_item.job_location == "Remote"
    assert job_item.job_ats_provider == "greenhouse"
    assert job_item.job_posting_date is not None
    # Original text fields untouched.
    assert job_item.signal_label == "Machine Learning Engineer"

    # Stage 4: persist via EvidenceRepository, then read back
    session_factory = await _make_session_factory()
    async with session_factory() as session:
        company_repo = CompanyRepository(session)
        evidence_repo = EvidenceRepository(session)
        company = await company_repo.get_or_create(domain="acme.com", name="Acme")
        evidence_repo.add_batch(company, normalized)
        await company_repo.commit()

    async with session_factory() as session:
        company = await CompanyRepository(session).get_or_create(domain="acme.com", name="Acme")
        rows = await EvidenceRepository(session).list_by_company(company.id)

    persisted_job = rows[0]
    assert persisted_job.job_title == "Machine Learning Engineer"
    assert persisted_job.job_department == "AI"
    assert persisted_job.job_location == "Remote"
    assert persisted_job.job_ats_provider == "greenhouse"
    assert persisted_job.job_posting_date is not None
    assert persisted_job.excerpt == GREENHOUSE_RESPONSE["jobs"][0]["content"].replace("<p>", "").replace(
        "</p>", ""
    )

    # Stage 5: the API's response schema
    record = EvidenceRecord.model_validate(persisted_job)
    assert record.job_title == "Machine Learning Engineer"
    assert record.job_department == "AI"
    assert record.job_location == "Remote"
    assert record.job_ats_provider == "greenhouse"
    assert record.job_posting_date is not None
    # Technology fields must remain null on jobs evidence.
    assert record.technology_name is None

    get_settings.cache_clear()
    monkeypatch.delenv("ENABLE_LIVE_JOBS", raising=False)
