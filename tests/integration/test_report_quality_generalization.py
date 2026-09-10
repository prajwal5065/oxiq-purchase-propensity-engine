"""End-to-end pipeline checks for the report-quality fixes: source
provenance, freshness weighting, confidence calibration, and headquarters
vs. office/facility location. Run for two unrelated companies (an Indian
food company and a US SaaS company) to guard against any of this having
been accidentally special-cased for one company's data shape.
"""
from datetime import UTC, datetime, timedelta

import pytest

from app.aggregation.purchase_aggregator import PurchaseAggregator
from app.decision.contradiction_detector import ContradictionDetector
from app.extraction.evidence_extractor import EvidenceExtractor
from app.models.signal import SignalSource
from app.schemas.signal import RawSignal
from app.scoring import ALL_SCORING_AGENTS
from app.services.evidence_normalizer import EvidenceNormalizer

NOW = datetime(2026, 8, 30, tzinfo=UTC)


def _company_profile_signal(url, locality, region, country, employees, founding_date):
    return RawSignal(
        source=SignalSource.COMPANY_PROFILE,
        category="industry_profile",
        payload={
            "headquarters": {"addressLocality": locality, "addressRegion": region, "addressCountry": country},
            "numberOfEmployees": employees,
            "foundingDate": founding_date,
        },
        url=url,
    )


def _job_signal(url, title, location, posted_at):
    return RawSignal(
        source=SignalSource.JOBS,
        category="engineering_hiring",
        payload={
            "title": title,
            "department": "Sales",
            "location": location,
            "posted_at": posted_at,
            "provider": "greenhouse",
            "description_snippet": "...",
        },
        url=url,
    )


def _news_signal(url, title):
    return RawSignal(source=SignalSource.SEARCH, category="news", payload={"title": title, "content": "..."}, url=url)


async def _run_pipeline(raw_signals: list[RawSignal], llm_items: list[dict]):
    import json

    extracted = EvidenceExtractor._parse_response(json.dumps(llm_items), raw_signals)
    normalized = EvidenceNormalizer().normalize(raw_signals=raw_signals, items=extracted)
    contradictions = ContradictionDetector().detect(normalized)
    agents = [agent_cls() for agent_cls in ALL_SCORING_AGENTS]
    import asyncio

    pillar_scores = await asyncio.gather(*(a.score("x.com", normalized) for a in agents))
    purchase_result = PurchaseAggregator().aggregate(company_domain="x.com", pillar_scores=list(pillar_scores))
    return normalized, contradictions, purchase_result


def _scenario(homepage_url, job_url, news_recent_url, news_old_url, locality, region, country, job_location):
    raw_signals = [
        _news_signal(news_recent_url, "Recent news"),
        _news_signal(news_old_url, "Old news"),
        _company_profile_signal(homepage_url, locality, region, country, "500", "2015-01-01"),
        _job_signal(job_url, "Regional Manager", job_location, (NOW - timedelta(days=10)).isoformat()),
    ]
    llm_items = [
        {
            "signal_label": "Recent development",
            "excerpt": "Something newsworthy happened recently",
            "source": "search",
            "signal_index": 0,
            "confidence": 0.95,
            "published_at": (NOW - timedelta(days=5)).isoformat(),
        },
        {
            "signal_label": "Old development",
            "excerpt": "Something happened a long time ago",
            "source": "news",
            "signal_index": 1,
            "confidence": 0.9,
            "published_at": "2018-01-01T00:00:00+00:00",
        },
        {
            "signal_label": "Company headquarters",
            "excerpt": "The company's headquarters",
            "source": "Company Profile",
            "signal_index": 2,
            "confidence": 0.9,
            "published_at": None,
        },
        {
            "signal_label": f"Hiring a Regional Manager in {job_location}",
            "excerpt": f"Now hiring a Regional Manager based in {job_location}",
            "source": "Greenhouse",
            "signal_index": 3,
            "confidence": 0.9,
            "published_at": (NOW - timedelta(days=10)).isoformat(),
        },
    ]
    return raw_signals, llm_items


GITS_FOOD = _scenario(
    homepage_url="https://www.gitsfood.com",
    job_url="https://boards.greenhouse.io/gitsfood/jobs/1",
    news_recent_url="https://www.thehindubusinessline.com/gits-food-recent",
    news_old_url="https://www.business-standard.com/gits-food-old-2018",
    locality="Pune",
    region="Maharashtra",
    country="IN",
    job_location="Mumbai, India",
)

WINGTIP_SAAS = _scenario(
    homepage_url="https://www.wingtipcloud.io",
    job_url="https://jobs.lever.co/wingtipcloud/1",
    news_recent_url="https://techcrunch.com/2026/07/wingtip-cloud-series-c",
    news_old_url="https://venturebeat.com/2016/wingtip-cloud-launch",
    locality="San Francisco",
    region="CA",
    country="US",
    job_location="New York, NY",
)


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_signals,llm_items", [GITS_FOOD, WINGTIP_SAAS])
async def test_source_provenance_replaces_generic_labels_with_real_domains(raw_signals, llm_items):
    normalized, _, _ = await _run_pipeline(raw_signals, llm_items)
    sources = {item.source for item in normalized}
    assert "search" not in sources
    assert "news" not in sources
    # The real outlet domains from the raw signals' URLs should be present.
    assert any(item.url and item.source in str(item.url) for item in normalized if item.category == "news" or True)


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_signals,llm_items", [GITS_FOOD, WINGTIP_SAAS])
async def test_headquarters_from_company_profile_is_never_the_job_posting_city(raw_signals, llm_items):
    normalized, contradictions, _ = await _run_pipeline(raw_signals, llm_items)

    hq_items = [i for i in normalized if i.location_kind == "headquarters"]
    office_items = [i for i in normalized if i.location_kind == "office"]

    assert len(hq_items) == 1
    assert len(office_items) == 1
    assert hq_items[0].location_name != office_items[0].location_name
    # A single office posting, with no second conflicting HQ source, must
    # never itself be flagged as a headquarters disagreement.
    assert not any(f.theme == "headquarters_conflict" for f in contradictions.findings)


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_signals,llm_items", [GITS_FOOD, WINGTIP_SAAS])
async def test_purchase_confidence_is_not_pinned_to_extraction_confidence(raw_signals, llm_items):
    """Every raw LLM item above has confidence >= 0.9, but the pillar
    scorers only saw a handful of search/company-profile-tier items with
    no corroboration - the calibrated confidence must land well under 1.0,
    not default to (approximately) the raw extraction confidence."""
    _, _, purchase_result = await _run_pipeline(raw_signals, llm_items)
    assert purchase_result.confidence < 0.5


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_signals,llm_items", [GITS_FOOD, WINGTIP_SAAS])
async def test_old_evidence_contributes_less_than_fresh_evidence_to_urgency(raw_signals, llm_items):
    normalized, _, _ = await _run_pipeline(raw_signals, llm_items)
    old_item = next(i for i in normalized if i.published_at and i.published_at.year == 2018 or (i.published_at and i.published_at < NOW - timedelta(days=365 * 2)))
    from app.scoring.time_decay import decay_weight

    recent_item = next(i for i in normalized if i.published_at and i.published_at > NOW - timedelta(days=30))
    assert decay_weight(old_item.published_at) < decay_weight(recent_item.published_at)
