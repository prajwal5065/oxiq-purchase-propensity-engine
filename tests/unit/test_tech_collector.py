import httpx
import pytest
import respx
from unittest.mock import patch, MagicMock

from app.collectors.tech_collector import TechCollector
from app.core.config import get_settings
from app.schemas.signal import CollectorStatus

BUILTWITH_API_URL = "https://api.builtwith.com/v23/api.json"

BUILTWITH_SUCCESS_RESPONSE = {
    "Results": [
        {
            "Result": {
                "Paths": [
                    {
                        "Technologies": [
                            {"Name": "React", "Tag": "javascript"},
                            {"Name": "AWS", "Tag": "iaas"},
                            {"Name": "React", "Tag": "javascript"}  # Duplicate
                        ]
                    }
                ]
            }
        }
    ]
}

BUILTWITH_ERROR_RESPONSE = {
    "Errors": [
        {"Message": "Insufficient quota"}
    ]
}


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_live_tech_detection", True)
    monkeypatch.setattr(settings, "builtwith_api_key", "test_key")


@pytest.mark.asyncio
@respx.mock
async def test_builtwith_success_skips_wappalyzer():
    respx.get(BUILTWITH_API_URL).mock(
        return_value=httpx.Response(200, json=BUILTWITH_SUCCESS_RESPONSE)
    )

    with patch("Wappalyzer.WebPage.new_from_url") as mock_new_from_url:
        collector = TechCollector()
        result = await collector.collect("acme.com")

        assert result.is_live is True
        assert len(result.signals) == 2
        techs = {s.payload["technology"] for s in result.signals}
        assert techs == {"React", "AWS"}
        assert all(s.payload["provider"] == "builtwith" for s in result.signals)
        mock_new_from_url.assert_not_called()


@pytest.mark.asyncio
@respx.mock
async def test_builtwith_429_quota_falls_back_to_wappalyzer():
    respx.get(BUILTWITH_API_URL).mock(return_value=httpx.Response(429))

    with patch("Wappalyzer.Wappalyzer") as mock_wappalyzer_cls:
        mock_instance = MagicMock()
        mock_wappalyzer_cls.latest.return_value = mock_instance
        mock_instance.analyze_with_categories.return_value = {
            "Google Analytics": {"categories": ["Analytics"]}
        }
        with patch("Wappalyzer.WebPage.new_from_url") as mock_webpage:
            collector = TechCollector()
            result = await collector.collect("acme.com")

            assert result.is_live is True
            assert len(result.signals) == 1
            assert result.signals[0].payload["technology"] == "Google Analytics"
            assert result.signals[0].payload["provider"] == "wappalyzer"
            assert any("Quota exceeded" in err for err in result.errors)
            mock_webpage.assert_called_once()


@pytest.mark.asyncio
@respx.mock
async def test_builtwith_api_error_payload_falls_back():
    respx.get(BUILTWITH_API_URL).mock(
        return_value=httpx.Response(200, json=BUILTWITH_ERROR_RESPONSE)
    )

    with patch("Wappalyzer.Wappalyzer") as mock_wappalyzer_cls:
        mock_instance = MagicMock()
        mock_wappalyzer_cls.latest.return_value = mock_instance
        mock_instance.analyze_with_categories.return_value = {}
        with patch("Wappalyzer.WebPage.new_from_url") as mock_webpage:
            collector = TechCollector()
            result = await collector.collect("acme.com")

            assert any("API Error - Insufficient quota" in err for err in result.errors)
            mock_webpage.assert_called_once()


@pytest.mark.asyncio
@respx.mock
async def test_builtwith_timeout_falls_back_to_wappalyzer():
    respx.get(BUILTWITH_API_URL).mock(side_effect=httpx.TimeoutException("Timeout"))

    with patch("Wappalyzer.Wappalyzer") as mock_wappalyzer_cls:
        mock_instance = MagicMock()
        mock_wappalyzer_cls.latest.return_value = mock_instance
        mock_instance.analyze_with_categories.return_value = {}
        with patch("Wappalyzer.WebPage.new_from_url") as mock_webpage:
            collector = TechCollector()
            result = await collector.collect("acme.com")

            assert any("Timeout" in err for err in result.errors)
            mock_webpage.assert_called_once()


@pytest.mark.asyncio
async def test_missing_builtwith_key_uses_wappalyzer_directly(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "builtwith_api_key", None)

    with patch("Wappalyzer.Wappalyzer") as mock_wappalyzer_cls:
        mock_instance = MagicMock()
        mock_wappalyzer_cls.latest.return_value = mock_instance
        mock_instance.analyze_with_categories.return_value = {
            "Salesforce": {"categories": ["CRM"]}
        }
        with patch("Wappalyzer.WebPage.new_from_url") as mock_webpage:
            collector = TechCollector()
            result = await collector.collect("acme.com")

            assert len(result.signals) == 1
            assert result.signals[0].payload["provider"] == "wappalyzer"
            assert any("No API key configured" in err for err in result.errors)
            mock_webpage.assert_called_once()


@pytest.mark.asyncio
@respx.mock
async def test_builtwith_key_is_never_leaked_in_errors():
    respx.get(BUILTWITH_API_URL).mock(return_value=httpx.Response(401))

    with patch("Wappalyzer.WebPage.new_from_url"):
        collector = TechCollector()
        result = await collector.collect("acme.com")
        
        for err in result.errors:
            assert "test_key" not in err
