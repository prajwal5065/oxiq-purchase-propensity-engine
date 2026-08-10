"""Search Collector - uses Tavily to find website, blog, careers, news,
press releases, AI initiatives, and product launch pages for a company.

Runs in stub mode (returns an empty-but-valid result, `is_live=False`) when
`ENABLE_LIVE_SEARCH` is off or `TAVILY_API_KEY` is unset, so the rest of the
pipeline can be built and tested without live credentials.
"""
from app.collectors.base import BaseCollector
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.signal import SignalSource
from app.schemas.signal import CollectorResult, CollectorStatus, RawSignal

logger = get_logger(__name__)

SEARCH_TOPICS = [
    ("website", "{domain} official website"),
    ("blog", "{domain} company blog"),
    ("careers", "{domain} careers jobs hiring"),
    ("news", "{domain} company news"),
    ("press_releases", "{domain} press release announcement"),
    ("ai_initiatives", "{domain} AI artificial intelligence initiative"),
    ("product_launches", "{domain} new product launch"),
]


class SearchCollector(BaseCollector):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def collect(self, company_domain: str) -> CollectorResult:
        if not self.settings.enable_live_search or not self.settings.tavily_api_key:
            logger.info("search_collector.stub_mode", domain=company_domain)
            return CollectorResult(
                company_domain=company_domain,
                source=SignalSource.SEARCH,
                signals=[],
                is_live=False,
                errors=["Live search disabled or TAVILY_API_KEY missing - ran in stub mode"],
                status=CollectorStatus.NOT_CONFIGURED,
            )

        signals: list[RawSignal] = []
        errors: list[str] = []
        try:
            from tavily import TavilyClient  # imported lazily so stub mode has no hard dep

            client = TavilyClient(api_key=self.settings.tavily_api_key)
            for category, query_template in SEARCH_TOPICS:
                query = query_template.format(domain=company_domain)
                try:
                    result = client.search(query=query, max_results=5)
                    for item in result.get("results", []):
                        signals.append(
                            RawSignal(
                                source=SignalSource.SEARCH,
                                category=category,
                                payload={
                                    "title": item.get("title"),
                                    "content": item.get("content"),
                                },
                                url=item.get("url"),
                            )
                        )
                except Exception as exc:  # noqa: BLE001 - one bad topic must not kill the collector
                    errors.append(f"{category}: {exc}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"tavily_client_init: {exc}")

        return CollectorResult(
            company_domain=company_domain,
            source=SignalSource.SEARCH,
            signals=signals,
            is_live=True,
            errors=errors,
        )
