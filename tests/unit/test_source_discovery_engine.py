import pytest

from app.collectors.company_profile_collector import CompanyProfileCollector
from app.collectors.github_collector import GitHubCollector
from app.collectors.search_collector import SearchCollector
from app.discovery.source_discovery_engine import SourceDiscoveryEngine


@pytest.mark.asyncio
async def test_discover_returns_every_catalog_entry():
    discovered = await SourceDiscoveryEngine().discover("acme.com")
    names = {d.name for d in discovered}
    assert names == {"search", "website", "tech", "news", "github", "jobs", "company", "social"}


@pytest.mark.asyncio
async def test_discover_marks_built_collectors_as_implemented():
    discovered = await SourceDiscoveryEngine().discover("acme.com")
    by_name = {d.name: d for d in discovered}
    assert by_name["search"].implemented is True
    assert by_name["github"].implemented is True
    assert by_name["company"].implemented is True


@pytest.mark.asyncio
async def test_discover_marks_unbuilt_sources_as_not_implemented():
    discovered = await SourceDiscoveryEngine().discover("acme.com")
    by_name = {d.name: d for d in discovered}
    assert by_name["jobs"].implemented is False
    assert by_name["social"].implemented is False


@pytest.mark.asyncio
async def test_collectors_to_run_only_returns_implemented_collectors():
    collectors = await SourceDiscoveryEngine().collectors_to_run("acme.com")
    assert len(collectors) == 6
    assert any(isinstance(c, SearchCollector) for c in collectors)
    assert any(isinstance(c, GitHubCollector) for c in collectors)
    assert any(isinstance(c, CompanyProfileCollector) for c in collectors)


@pytest.mark.asyncio
async def test_not_implemented_labels_lists_only_unbuilt_sources():
    discovered = await SourceDiscoveryEngine().discover("acme.com")
    labels = SourceDiscoveryEngine.not_implemented_labels(discovered)
    assert len(labels) == 2
    assert any("Jobs" in label for label in labels)
    assert any("Social" in label for label in labels)
