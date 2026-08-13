import pytest

from app.collectors.company_profile_collector import CompanyProfileCollector
from app.collectors.github_collector import GitHubCollector
from app.collectors.jobs_collector import JobsCollector
from app.collectors.search_collector import SearchCollector
from app.collectors.tech_collector import TechCollector
from app.collectors.website_collector import WebsiteCollector
from app.schemas.signal import CollectorStatus


@pytest.mark.asyncio
async def test_search_collector_stub_mode_without_key():
    result = await SearchCollector().collect("acme.com")
    assert result.is_live is False
    assert result.signals == []
    assert result.errors


@pytest.mark.asyncio
async def test_website_collector_stub_mode_by_default():
    result = await WebsiteCollector().collect("acme.com")
    assert result.is_live is False
    assert result.signals == []


@pytest.mark.asyncio
async def test_tech_collector_stub_mode_by_default():
    result = await TechCollector().collect("acme.com")
    assert result.is_live is False
    assert result.signals == []


@pytest.mark.asyncio
async def test_github_collector_stub_mode_by_default():
    result = await GitHubCollector().collect("acme.com")
    assert result.is_live is False
    assert result.signals == []
    assert result.resolved_status == CollectorStatus.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_company_profile_collector_stub_mode_by_default():
    result = await CompanyProfileCollector().collect("acme.com")
    assert result.is_live is False
    assert result.signals == []
    assert result.resolved_status == CollectorStatus.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_jobs_collector_stub_mode_by_default():
    result = await JobsCollector().collect("acme.com")
    assert result.is_live is False
    assert result.signals == []
    assert result.resolved_status == CollectorStatus.NOT_CONFIGURED
