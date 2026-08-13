import httpx
import pytest
import respx

from app.collectors.company_profile_collector import CompanyProfileCollector
from app.core.config import get_settings
from app.schemas.signal import CollectorStatus

JSON_LD_HTML = """
<html><head>
<meta name="description" content="Acme builds enterprise automation software.">
<meta property="og:site_name" content="Acme Inc">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Acme Inc",
  "industry": "Software",
  "numberOfEmployees": "500-1000",
  "foundingDate": "2015",
  "address": {"@type": "PostalAddress", "addressLocality": "Austin", "addressCountry": "US"}
}
</script>
</head>
<body>
  <p>We run our platform on AWS and Azure, and use machine learning across our product.</p>
  <p>Our REST API and mobile app support a fully cloud-native SaaS deployment.</p>
</body></html>
"""

WIKIDATA_SEARCH_RESPONSE = {"search": [{"id": "Q12345", "label": "Acme Inc"}]}
WIKIDATA_CLAIMS_RESPONSE = {
    "entities": {
        "Q12345": {
            "claims": {
                "P452": [{"mainsnak": {"datavalue": {"value": {"id": "Q7397"}}}}],
                "P1128": [{"mainsnak": {"datavalue": {"value": {"amount": "+750"}}}}],
            }
        }
    }
}


@pytest.fixture(autouse=True)
def _enable_live_company_profile(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_LIVE_COMPANY_PROFILE", "true")
    yield
    get_settings.cache_clear()
    monkeypatch.delenv("ENABLE_LIVE_COMPANY_PROFILE", raising=False)


@pytest.mark.asyncio
async def test_stub_mode_returns_not_configured_when_flag_off(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_live_company_profile", False)
    result = await CompanyProfileCollector().collect("acme.com")
    assert result.is_live is False
    assert result.signals == []
    assert result.resolved_status == CollectorStatus.NOT_CONFIGURED


@pytest.mark.asyncio
@respx.mock
async def test_json_ld_and_wikidata_both_produce_signals():
    respx.get("https://acme.com").mock(return_value=httpx.Response(200, text=JSON_LD_HTML))
    respx.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities"}).mock(
        return_value=httpx.Response(200, json=WIKIDATA_SEARCH_RESPONSE)
    )
    respx.get("https://www.wikidata.org/w/api.php", params={"action": "wbgetentities"}).mock(
        return_value=httpx.Response(200, json=WIKIDATA_CLAIMS_RESPONSE)
    )

    result = await CompanyProfileCollector().collect("acme.com")

    assert result.is_live is True
    assert result.resolved_status == CollectorStatus.SUCCESS
    categories = {s.category for s in result.signals}
    assert "industry_profile" in categories
    assert "cloud_ai_ml_technology" in categories
    assert "digital_maturity" in categories
    assert "company_registry" in categories


@pytest.mark.asyncio
@respx.mock
async def test_json_ld_extracts_organization_fields():
    respx.get("https://acme.com").mock(return_value=httpx.Response(200, text=JSON_LD_HTML))
    respx.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities"}).mock(
        return_value=httpx.Response(200, json={"search": []})
    )

    result = await CompanyProfileCollector().collect("acme.com")

    profile_signals = [s for s in result.signals if s.category == "industry_profile"]
    assert profile_signals
    combined_payload = {k: v for s in profile_signals for k, v in s.payload.items()}
    assert combined_payload.get("numberOfEmployees") == "500-1000"
    assert combined_payload.get("industry") == "Software"


@pytest.mark.asyncio
@respx.mock
async def test_cloud_ai_ml_keyword_scan_matches_expected_terms():
    respx.get("https://acme.com").mock(return_value=httpx.Response(200, text=JSON_LD_HTML))
    respx.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities"}).mock(
        return_value=httpx.Response(200, json={"search": []})
    )

    result = await CompanyProfileCollector().collect("acme.com")

    cloud_signal = next(s for s in result.signals if s.category == "cloud_ai_ml_technology")
    matched = set(cloud_signal.payload["matched_terms"])
    assert {"aws", "azure", "machine learning"} <= matched


@pytest.mark.asyncio
@respx.mock
async def test_wikidata_no_match_is_not_an_error():
    respx.get("https://acme.com").mock(return_value=httpx.Response(200, text="<html></html>"))
    respx.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities"}).mock(
        return_value=httpx.Response(200, json={"search": []})
    )

    result = await CompanyProfileCollector().collect("acme.com")

    assert result.is_live is True
    assert not any(s.category == "company_registry" for s in result.signals)
    assert result.errors == []


@pytest.mark.asyncio
@respx.mock
async def test_one_provider_failing_does_not_sink_the_other():
    respx.get("https://acme.com").mock(return_value=httpx.Response(500))
    respx.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities"}).mock(
        return_value=httpx.Response(200, json=WIKIDATA_SEARCH_RESPONSE)
    )
    respx.get("https://www.wikidata.org/w/api.php", params={"action": "wbgetentities"}).mock(
        return_value=httpx.Response(200, json=WIKIDATA_CLAIMS_RESPONSE)
    )

    result = await CompanyProfileCollector().collect("acme.com")

    assert result.is_live is True
    assert result.errors  # the homepage fetch failure is recorded
    assert any(s.category == "company_registry" for s in result.signals)  # wikidata still succeeded


@pytest.mark.asyncio
@respx.mock
async def test_no_signals_and_no_errors_resolves_to_no_results():
    respx.get("https://acme.com").mock(return_value=httpx.Response(200, text="<html></html>"))
    respx.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities"}).mock(
        return_value=httpx.Response(200, json={"search": []})
    )

    result = await CompanyProfileCollector().collect("acme.com")

    assert result.signals == []
    assert result.errors == []
    assert result.resolved_status == CollectorStatus.NO_RESULTS
