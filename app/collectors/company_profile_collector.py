"""Company & Technology Intelligence Collector.

Covers the gap the SOURCE_CATALOG has long flagged as unimplemented
("Company Data (Crunchbase / OpenCorporates)"): company size/capacity,
industry/profile, technology stack, cloud/AI/ML technologies, and digital
maturity signals - fed through the same Evidence Store and Decision
Intelligence pipeline every other collector uses, not a separate scoring
system. `capacity_scorer` and `digital_maturity_scorer` already look for
this vocabulary (employees, headcount, industry, aws, azure, kubernetes,
machine learning...); this collector's job is just to put grounded raw
text in front of the Evidence Extractor so those existing pillars have
something to match against.

No paid APIs yet, by design - both providers below are free and
unauthenticated:

- `JsonLdOrganizationProvider` fetches the company's own homepage and
  reads whatever schema.org Organization markup and meta tags it publishes
  (industry, employee count, founding date, HQ, description), plus a
  lightweight keyword scan of the visible page text for cloud/AI-ML
  technology and general digital-maturity signals (SaaS/API/mobile-app
  language) - a cheap complement to the Wappalyzer-based TechCollector,
  not a replacement for it.
- `WikidataProvider` looks the company up in Wikidata's free public API
  for the same class of facts (industry, employees, founding date, HQ)
  from an independent, third-party source. Two independently-sourced
  takes on "how big is this company" is exactly the kind of overlap the
  existing Contradiction Detection engine is built to surface.

Providers are pluggable: `CompanyProfileCollector` just fans out to
whatever's in `PROVIDERS` and merges the results, so wiring in a future
paid provider (Crunchbase, Clearbit, ZoomInfo...) later is one more
`CompanyProfileProvider` subclass, not a change to this collector, the
orchestrator, or the SOURCE_CATALOG entry.
"""
import asyncio
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from app.collectors.base import BaseCollector
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.signal import SignalSource
from app.schemas.signal import CollectorResult, CollectorStatus, RawSignal

logger = get_logger(__name__)

# Wappalyzer (TechCollector) already fingerprints frameworks/CRM/marketing
# tools by parsing rendered pages. This list is deliberately narrower and
# complementary: named cloud/AI-ML vendors and platforms worth flagging
# even from a single unrendered homepage fetch.
CLOUD_AI_ML_KEYWORDS = {
    "aws", "amazon web services", "microsoft azure", "azure", "google cloud",
    "gcp", "openai", "anthropic", "claude", "chatgpt", "machine learning",
    "artificial intelligence", "generative ai", "large language model",
    "llm", "tensorflow", "pytorch", "hugging face", "vertex ai",
    "amazon bedrock", "azure openai", "snowflake", "databricks",
}

DIGITAL_MATURITY_KEYWORDS = {
    "api", "rest api", "graphql", "mobile app", "ios app", "android app",
    "saas", "cloud-native", "cloud native", "microservices", "kubernetes",
    "ci/cd", "devops", "digital transformation", "self-service platform",
}

MAX_KEYWORD_HITS_PER_GROUP = 8


@dataclass
class ProviderOutput:
    signals: list[RawSignal] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class CompanyProfileProvider(ABC):
    """One free-text or structured source of company/technology facts.

    Every provider must degrade gracefully - a provider that can't reach
    its source, gets a 404, or finds nothing returns an empty/error-noted
    ProviderOutput rather than raising, so one provider's failure never
    takes the others down with it (see `CompanyProfileCollector.collect`).
    """

    name: str

    @abstractmethod
    async def fetch(self, company_domain: str, timeout_seconds: float) -> ProviderOutput:
        raise NotImplementedError


class JsonLdOrganizationProvider(CompanyProfileProvider):
    """Reads the company's own homepage: schema.org Organization JSON-LD,
    meta tags, and a keyword scan of the visible text - all from a single
    unauthenticated GET, no headless browser required."""

    name = "jsonld_homepage"

    _JSONLD_RE = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    _META_RE = re.compile(r"<meta\s+([^>]+)>", re.IGNORECASE)
    _TAG_RE = re.compile(r"<[^>]+>")

    # schema.org Organization/Corporation fields worth surfacing as evidence.
    _ORG_FIELDS = ("industry", "numberOfEmployees", "foundingDate", "description", "slogan")

    async def fetch(self, company_domain: str, timeout_seconds: float) -> ProviderOutput:
        signals: list[RawSignal] = []
        errors: list[str] = []
        url = f"https://{company_domain.rstrip('/')}"

        try:
            import httpx

            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "OxiQ-CompanyProfileCollector/1.0"})
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {exc}")
            return ProviderOutput(signals=signals, errors=errors)

        if response.status_code != 200:
            errors.append(f"{url}: unexpected status {response.status_code}")
            return ProviderOutput(signals=signals, errors=errors)

        html = response.text
        signals.extend(self._extract_json_ld(html, url))
        signals.extend(self._extract_meta_tags(html, url))
        signals.extend(self._scan_keywords(html, url))
        return ProviderOutput(signals=signals, errors=errors)

    def _extract_json_ld(self, html: str, url: str) -> list[RawSignal]:
        signals: list[RawSignal] = []
        for raw_block in self._JSONLD_RE.findall(html):
            try:
                data = json.loads(raw_block.strip())
            except json.JSONDecodeError:
                continue

            for entry in data if isinstance(data, list) else [data]:
                if not isinstance(entry, dict):
                    continue
                entry_type = str(entry.get("@type", "")).lower()
                if "organization" not in entry_type and "corporation" not in entry_type:
                    continue

                fields_present = {f: entry[f] for f in self._ORG_FIELDS if entry.get(f)}
                if fields_present:
                    signals.append(
                        RawSignal(
                            source=SignalSource.COMPANY_PROFILE,
                            category="industry_profile",
                            payload={"schema_type": entry.get("@type"), **fields_present},
                            url=url,
                        )
                    )

                address = entry.get("address")
                if isinstance(address, dict) and address:
                    signals.append(
                        RawSignal(
                            source=SignalSource.COMPANY_PROFILE,
                            category="industry_profile",
                            payload={"headquarters": address},
                            url=url,
                        )
                    )

        return signals

    def _extract_meta_tags(self, html: str, url: str) -> list[RawSignal]:
        wanted = {"description", "og:description", "keywords", "og:site_name"}
        found: dict[str, str] = {}

        for attrs_blob in self._META_RE.findall(html):
            name_match = re.search(r'(?:name|property)=["\']([^"\']+)["\']', attrs_blob, re.IGNORECASE)
            content_match = re.search(r'content=["\']([^"\']*)["\']', attrs_blob, re.IGNORECASE)
            if not name_match or not content_match:
                continue
            tag_name = name_match.group(1).lower()
            if tag_name in wanted and content_match.group(1).strip():
                found[tag_name] = content_match.group(1).strip()

        if not found:
            return []

        return [
            RawSignal(
                source=SignalSource.COMPANY_PROFILE,
                category="industry_profile",
                payload={"meta_tags": found},
                url=url,
            )
        ]

    def _scan_keywords(self, html: str, url: str) -> list[RawSignal]:
        text = self._TAG_RE.sub(" ", html).lower()
        signals: list[RawSignal] = []

        cloud_ai_hits = sorted({kw for kw in CLOUD_AI_ML_KEYWORDS if kw in text})[:MAX_KEYWORD_HITS_PER_GROUP]
        if cloud_ai_hits:
            signals.append(
                RawSignal(
                    source=SignalSource.COMPANY_PROFILE,
                    category="cloud_ai_ml_technology",
                    payload={"matched_terms": cloud_ai_hits},
                    url=url,
                )
            )

        maturity_hits = sorted({kw for kw in DIGITAL_MATURITY_KEYWORDS if kw in text})[:MAX_KEYWORD_HITS_PER_GROUP]
        if maturity_hits:
            signals.append(
                RawSignal(
                    source=SignalSource.COMPANY_PROFILE,
                    category="digital_maturity",
                    payload={"matched_terms": maturity_hits},
                    url=url,
                )
            )

        return signals


class WikidataProvider(CompanyProfileProvider):
    """Looks the company up in Wikidata's free, unauthenticated public API -
    an independent third-party source for the same class of facts the
    homepage self-reports (industry, employee count, founding date, HQ)."""

    name = "wikidata"

    # Wikidata property IDs for the facts we care about.
    _PROPERTY_LABELS: ClassVar[dict[str, str]] = {
        "P452": "industry",
        "P1128": "employee_count",
        "P571": "founding_date",
        "P159": "headquarters_location",
    }

    async def fetch(self, company_domain: str, timeout_seconds: float) -> ProviderOutput:
        errors: list[str] = []
        company_name = company_domain.split(".")[0]
        settings = get_settings()

        try:
            import httpx

            async with httpx.AsyncClient(
                base_url=settings.wikidata_api_base.rsplit("/w/api.php", 1)[0],
                timeout=timeout_seconds,
                headers={"User-Agent": "OxiQ-CompanyProfileCollector/1.0"},
            ) as client:
                entity_id = await self._search_entity(client, company_name, errors)
                if entity_id is None:
                    return ProviderOutput(signals=[], errors=errors)

                claims = await self._fetch_claims(client, entity_id, errors)
                signals = self._build_signals(entity_id, claims)
                return ProviderOutput(signals=signals, errors=errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"wikidata_client_init: {exc}")
            return ProviderOutput(signals=[], errors=errors)

    async def _search_entity(self, client, company_name: str, errors: list[str]) -> str | None:
        try:
            response = await client.get(
                "/w/api.php",
                params={
                    "action": "wbsearchentities",
                    "search": company_name,
                    "language": "en",
                    "format": "json",
                    "type": "item",
                    "limit": 1,
                },
            )
            if response.status_code != 200:
                errors.append(f"wbsearchentities: unexpected status {response.status_code}")
                return None
            results = response.json().get("search", [])
            return results[0]["id"] if results else None
        except Exception as exc:  # noqa: BLE001
            errors.append(f"wbsearchentities: {exc}")
            return None

    async def _fetch_claims(self, client, entity_id: str, errors: list[str]) -> dict:
        try:
            response = await client.get(
                "/w/api.php",
                params={
                    "action": "wbgetentities",
                    "ids": entity_id,
                    "props": "claims",
                    "format": "json",
                },
            )
            if response.status_code != 200:
                errors.append(f"wbgetentities: unexpected status {response.status_code}")
                return {}
            return response.json().get("entities", {}).get(entity_id, {}).get("claims", {})
        except Exception as exc:  # noqa: BLE001
            errors.append(f"wbgetentities: {exc}")
            return {}

    def _build_signals(self, entity_id: str, claims: dict) -> list[RawSignal]:
        facts: dict[str, object] = {}
        for property_id, label in self._PROPERTY_LABELS.items():
            values = claims.get(property_id)
            if not values:
                continue
            snak_value = self._first_snak_value(values)
            if snak_value is not None:
                facts[label] = snak_value

        if not facts:
            return []

        return [
            RawSignal(
                source=SignalSource.COMPANY_PROFILE,
                category="company_registry",
                payload={"wikidata_id": entity_id, **facts},
                url=f"https://www.wikidata.org/wiki/{entity_id}",
            )
        ]

    @staticmethod
    def _first_snak_value(values: list[dict]) -> object | None:
        try:
            datavalue = values[0]["mainsnak"]["datavalue"]["value"]
        except (KeyError, IndexError, TypeError):
            return None
        # Wikidata quantities/entity-refs are objects; amount/id is the useful bit.
        if isinstance(datavalue, dict):
            return datavalue.get("amount") or datavalue.get("id") or datavalue.get("time") or str(datavalue)
        return datavalue


PROVIDERS: list[type[CompanyProfileProvider]] = [JsonLdOrganizationProvider, WikidataProvider]


class CompanyProfileCollector(BaseCollector):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.providers = [provider_cls() for provider_cls in PROVIDERS]

    async def collect(self, company_domain: str) -> CollectorResult:
        if not self.settings.enable_live_company_profile:
            logger.info("company_profile_collector.stub_mode", domain=company_domain)
            return CollectorResult(
                company_domain=company_domain,
                source=SignalSource.COMPANY_PROFILE,
                signals=[],
                is_live=False,
                errors=[
                    "Live company profile collection disabled (ENABLE_LIVE_COMPANY_PROFILE=false) - ran in stub mode"
                ],
                status=CollectorStatus.NOT_CONFIGURED,
            )

        timeout = float(self.settings.company_profile_timeout_seconds)
        outputs = await asyncio.gather(
            *(provider.fetch(company_domain, timeout) for provider in self.providers),
            return_exceptions=True,
        )

        signals: list[RawSignal] = []
        errors: list[str] = []
        for provider, output in zip(self.providers, outputs, strict=True):
            if isinstance(output, BaseException):
                # A provider that raises despite the try/except in its own
                # `fetch` (e.g. an import error) still shouldn't sink the
                # others - record it and move on.
                errors.append(f"{provider.name}: {output}")
                continue
            signals.extend(output.signals)
            errors.extend(output.errors)

        return CollectorResult(
            company_domain=company_domain,
            source=SignalSource.COMPANY_PROFILE,
            signals=signals,
            is_live=True,
            errors=errors,
        )
