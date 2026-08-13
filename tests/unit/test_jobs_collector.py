import httpx
import pytest
import respx

from app.collectors.jobs_collector import JobsCollector, classify_hiring_category
from app.core.config import get_settings
from app.schemas.signal import CollectorStatus

GREENHOUSE_RESPONSE = {
    "jobs": [
        {
            "id": 1,
            "title": "Machine Learning Engineer",
            "updated_at": "2026-08-01T12:00:00-04:00",
            "location": {"name": "Remote"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
            "content": "<p>Join our AI team. We are hiring a Machine Learning Engineer to build models.</p>",
            "departments": [{"name": "AI"}],
        },
        {
            "id": 2,
            "title": "Site Reliability Engineer",
            "updated_at": "2026-07-15T09:00:00-04:00",
            "location": {"name": "Austin, TX"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
            "content": "<p>Own our Kubernetes infrastructure and cloud platform.</p>",
            "departments": [{"name": "Infrastructure"}],
        },
    ]
}

LEVER_RESPONSE = [
    {
        "id": "abc",
        "text": "Account Coordinator",
        "createdAt": 1753900800000,  # 2025-07-30 UTC in ms
        "categories": {"team": "Sales", "location": "New York"},
        "hostedUrl": "https://jobs.lever.co/acme/abc",
        "descriptionPlain": "Support the sales team with account management.",
    }
]


@pytest.fixture(autouse=True)
def _enable_live_jobs(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_LIVE_JOBS", "true")
    yield
    get_settings.cache_clear()
    monkeypatch.delenv("ENABLE_LIVE_JOBS", raising=False)


# --- classify_hiring_category ---


def test_classify_ai_ml_hiring():
    assert classify_hiring_category("Machine Learning Engineer", "AI", "builds models") == "ai_ml_hiring"


def test_classify_security_hiring():
    assert classify_hiring_category("Security Engineer", "InfoSec", "") == "security_hiring"


def test_classify_cloud_devops_hiring():
    assert classify_hiring_category("Site Reliability Engineer", "Infra", "kubernetes") == "cloud_devops_hiring"


def test_classify_data_hiring():
    assert classify_hiring_category("Data Engineer", "Data", "etl pipelines") == "data_hiring"


def test_classify_engineering_hiring():
    assert classify_hiring_category("Backend Engineer", "Engineering", "") == "engineering_hiring"


def test_classify_falls_back_to_general_hiring():
    assert classify_hiring_category("Account Coordinator", "Sales", "") == "general_hiring"


def test_classify_security_wins_over_ai_ml_when_both_present():
    """Deliberate tie-break: an 'AI Security Engineer' role is checked
    against security keywords first."""
    assert classify_hiring_category("AI Security Engineer", "", "") == "security_hiring"


# --- stub mode ---


@pytest.mark.asyncio
async def test_stub_mode_returns_not_configured_when_flag_off(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("ENABLE_LIVE_JOBS", raising=False)
    result = await JobsCollector().collect("acme.com")
    assert result.is_live is False
    assert result.signals == []
    assert result.resolved_status == CollectorStatus.NOT_CONFIGURED
    get_settings.cache_clear()


# --- SUCCESS ---


@pytest.mark.asyncio
@respx.mock
async def test_success_extracts_per_job_fields_from_both_providers():
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
        return_value=httpx.Response(200, json=GREENHOUSE_RESPONSE)
    )
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(200, json=LEVER_RESPONSE))

    result = await JobsCollector().collect("acme.com")

    assert result.is_live is True
    assert result.resolved_status == CollectorStatus.SUCCESS
    assert len(result.signals) == 3

    ml_signal = next(s for s in result.signals if s.payload["title"] == "Machine Learning Engineer")
    assert ml_signal.category == "ai_ml_hiring"
    assert ml_signal.payload["department"] == "AI"
    assert ml_signal.payload["location"] == "Remote"
    assert ml_signal.payload["posted_at"] == "2026-08-01T12:00:00-04:00"
    assert ml_signal.url == "https://boards.greenhouse.io/acme/jobs/1"
    assert ml_signal.payload["provider"] == "greenhouse"
    assert "hiring a Machine Learning Engineer" in ml_signal.payload["description_snippet"]
    assert "<p>" not in ml_signal.payload["description_snippet"]

    sre_signal = next(s for s in result.signals if s.payload["title"] == "Site Reliability Engineer")
    assert sre_signal.category == "cloud_devops_hiring"

    lever_signal = next(s for s in result.signals if s.payload["title"] == "Account Coordinator")
    assert lever_signal.category == "general_hiring"
    assert lever_signal.payload["provider"] == "lever"
    assert lever_signal.payload["department"] == "Sales"
    assert lever_signal.payload["location"] == "New York"
    assert lever_signal.url == "https://jobs.lever.co/acme/abc"
    assert lever_signal.payload["posted_at"].startswith("2025-07-30")


@pytest.mark.asyncio
@respx.mock
async def test_success_when_only_one_provider_has_a_board():
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
        return_value=httpx.Response(200, json=GREENHOUSE_RESPONSE)
    )
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(404))

    result = await JobsCollector().collect("acme.com")

    assert result.resolved_status == CollectorStatus.SUCCESS
    assert len(result.signals) == 2
    assert result.errors == []  # the Lever 404 must not surface as an error


# --- NO_RESULTS ---


@pytest.mark.asyncio
@respx.mock
async def test_no_results_when_neither_provider_has_a_board():
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(return_value=httpx.Response(404))
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(404))

    result = await JobsCollector().collect("acme.com")

    assert result.is_live is True
    assert result.signals == []
    assert result.errors == []
    assert result.resolved_status == CollectorStatus.NO_RESULTS


@pytest.mark.asyncio
@respx.mock
async def test_no_results_when_board_exists_but_has_zero_open_postings():
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
        return_value=httpx.Response(200, json={"jobs": []})
    )
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(200, json=[]))

    result = await JobsCollector().collect("acme.com")

    assert result.signals == []
    assert result.resolved_status == CollectorStatus.NO_RESULTS


# --- BLOCKED ---


@pytest.mark.asyncio
@respx.mock
async def test_blocked_when_both_providers_rate_limited():
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(return_value=httpx.Response(429))
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(403))

    result = await JobsCollector().collect("acme.com")

    assert result.signals == []
    assert result.resolved_status == CollectorStatus.BLOCKED


# --- TIMEOUT ---


@pytest.mark.asyncio
@respx.mock
async def test_timeout_when_both_providers_time_out():
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(side_effect=httpx.ConnectTimeout("timed out"))
    respx.get("https://api.lever.co/v0/postings/acme").mock(side_effect=httpx.ReadTimeout("timed out"))

    result = await JobsCollector().collect("acme.com")

    assert result.signals == []
    assert result.resolved_status == CollectorStatus.TIMEOUT


# --- ERROR ---


@pytest.mark.asyncio
@respx.mock
async def test_error_when_both_providers_return_unexpected_status():
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(return_value=httpx.Response(500))
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(502))

    result = await JobsCollector().collect("acme.com")

    assert result.signals == []
    assert result.resolved_status == CollectorStatus.ERROR


# --- missing data must never become negative evidence ---


@pytest.mark.asyncio
@respx.mock
async def test_missing_board_produces_no_errors_and_no_negative_signal():
    """A company with no discoverable ATS board should look exactly like
    'we don't know' (NO_RESULTS, zero errors) - never like a discovered
    negative fact about the company's hiring."""
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(return_value=httpx.Response(404))
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(404))

    result = await JobsCollector().collect("acme.com")

    assert result.errors == []
    assert result.signals == []
    assert result.resolved_status != CollectorStatus.ERROR
    assert result.resolved_status != CollectorStatus.BLOCKED


@pytest.mark.asyncio
@respx.mock
async def test_jobs_capped_at_max_per_provider():
    many_jobs = {
        "jobs": [
            {
                "id": i,
                "title": f"Software Engineer {i}",
                "updated_at": "2026-08-01T12:00:00-04:00",
                "location": {"name": "Remote"},
                "absolute_url": f"https://boards.greenhouse.io/acme/jobs/{i}",
                "content": "",
                "departments": [{"name": "Engineering"}],
            }
            for i in range(75)
        ]
    }
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
        return_value=httpx.Response(200, json=many_jobs)
    )
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(404))

    result = await JobsCollector().collect("acme.com")
    assert len(result.signals) == 50
