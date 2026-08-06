import pytest

from app.collectors.search_collector import SearchCollector
from app.collectors.tech_collector import TechCollector
from app.collectors.website_collector import WebsiteCollector


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
