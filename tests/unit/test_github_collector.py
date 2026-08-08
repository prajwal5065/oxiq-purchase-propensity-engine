import httpx
import pytest
import respx

from app.collectors.github_collector import GitHubCollector
from app.core.config import get_settings
from app.schemas.signal import CollectorStatus


@pytest.fixture(autouse=True)
def _enable_live_github(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_LIVE_GITHUB", "true")
    yield
    get_settings.cache_clear()
    monkeypatch.delenv("ENABLE_LIVE_GITHUB", raising=False)


@pytest.mark.asyncio
@respx.mock
async def test_org_found_with_repos_produces_signals():
    respx.get("https://api.github.com/orgs/acme").mock(
        return_value=httpx.Response(200, json={"login": "acme", "html_url": "https://github.com/acme"})
    )
    respx.get("https://api.github.com/orgs/acme/repos").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": "acme-ml-platform",
                    "description": "Our internal machine-learning platform",
                    "topics": ["ai", "python"],
                    "language": "Python",
                    "stargazers_count": 42,
                    "pushed_at": "2026-08-01T00:00:00Z",
                    "html_url": "https://github.com/acme/acme-ml-platform",
                },
                {
                    "name": "acme-website",
                    "description": "Marketing site",
                    "topics": [],
                    "language": "TypeScript",
                    "stargazers_count": 3,
                    "pushed_at": "2026-07-01T00:00:00Z",
                    "html_url": "https://github.com/acme/acme-website",
                },
            ],
        )
    )

    result = await GitHubCollector().collect("acme.com")

    assert result.is_live is True
    assert result.resolved_status == CollectorStatus.SUCCESS
    categories = {s.category for s in result.signals}
    assert "engineering_activity" in categories
    assert "languages" in categories
    assert "ai_projects" in categories  # acme-ml-platform should be flagged


@pytest.mark.asyncio
@respx.mock
async def test_org_and_user_both_404_is_no_results_not_error():
    respx.get("https://api.github.com/orgs/acme").mock(return_value=httpx.Response(404))
    respx.get("https://api.github.com/users/acme").mock(return_value=httpx.Response(404))

    result = await GitHubCollector().collect("acme.com")

    assert result.is_live is True
    assert result.signals == []
    assert result.resolved_status == CollectorStatus.NO_RESULTS


@pytest.mark.asyncio
@respx.mock
async def test_rate_limited_org_lookup_is_blocked_not_silent_failure():
    respx.get("https://api.github.com/orgs/acme").mock(return_value=httpx.Response(403))

    result = await GitHubCollector().collect("acme.com")

    assert result.is_live is True
    assert result.signals == []
    assert result.errors
    assert result.resolved_status == CollectorStatus.BLOCKED


@pytest.mark.asyncio
@respx.mock
async def test_user_found_when_org_lookup_404s():
    respx.get("https://api.github.com/orgs/acme").mock(return_value=httpx.Response(404))
    respx.get("https://api.github.com/users/acme").mock(
        return_value=httpx.Response(200, json={"login": "acme", "html_url": "https://github.com/acme"})
    )
    respx.get("https://api.github.com/users/acme/repos").mock(return_value=httpx.Response(200, json=[]))

    result = await GitHubCollector().collect("acme.com")

    assert result.is_live is True
    assert result.signals == []  # account found but no repos -> no signals, still not an error
    assert result.errors == []
