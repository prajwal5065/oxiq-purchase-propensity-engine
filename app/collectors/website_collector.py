"""Website Collector - uses Crawl4AI to pull clean markdown from a
company's about, careers, product, pricing, customers, and blog pages.

Stub mode (`ENABLE_LIVE_CRAWL=false`) returns an empty-but-valid result so
downstream layers can be developed without a headless browser dependency.
"""
from urllib.parse import urlparse

from app.collectors.base import BaseCollector
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.signal import SignalSource
from app.schemas.signal import CollectorResult, CollectorStatus, RawSignal

logger = get_logger(__name__)

TARGET_PATHS = {
    "about": ["/about", "/about-us", "/company"],
    "careers": ["/careers", "/jobs"],
    "product": ["/product", "/products", "/platform"],
    "pricing": ["/pricing"],
    "customers": ["/customers", "/case-studies"],
    "blog": ["/blog", "/news"],
}


def _is_valid_url(url: str) -> bool:
    """Return True only if the URL has a valid scheme and a hostname with no spaces."""
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
            and " " not in parsed.netloc
        )
    except Exception:  # noqa: BLE001
        return False


class WebsiteCollector(BaseCollector):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def collect(self, company_domain: str) -> CollectorResult:
        if not self.settings.enable_live_crawl:
            logger.info("website_collector.stub_mode", domain=company_domain)
            return CollectorResult(
                company_domain=company_domain,
                source=SignalSource.WEBSITE,
                signals=[],
                is_live=False,
                errors=["Live crawling disabled (ENABLE_LIVE_CRAWL=false) - ran in stub mode"],
                status=CollectorStatus.NOT_CONFIGURED,
            )

        # Guard: reject non-domain values (spaces indicate a company name was passed)
        if " " in company_domain:
            logger.warning(
                "website_collector.invalid_domain",
                domain=company_domain,
                reason="domain contains spaces; skipping crawl",
            )
            return CollectorResult(
                company_domain=company_domain,
                source=SignalSource.WEBSITE,
                signals=[],
                is_live=False,
                errors=[f"Invalid domain '{company_domain}' (contains spaces). Crawl skipped."],
                status=CollectorStatus.FAILED,
            )

        signals: list[RawSignal] = []
        errors: list[str] = []
        try:
            from crawl4ai import AsyncWebCrawler  # imported lazily so stub mode has no hard dep

            async with AsyncWebCrawler(headless=self.settings.crawl4ai_headless) as crawler:
                for category, paths in TARGET_PATHS.items():
                    for path in paths:
                        url = f"https://{company_domain.rstrip('/')}{path}"
                        if not _is_valid_url(url):
                            logger.warning(
                                "website_collector.invalid_url",
                                url=url,
                                category=category,
                            )
                            errors.append(f"{category}:{path}: skipped — invalid URL '{url}'")
                            continue
                        try:
                            result = await crawler.arun(
                                url=url, timeout=self.settings.crawl4ai_timeout_seconds
                            )
                            if result and getattr(result, "success", False):
                                signals.append(
                                    RawSignal(
                                        source=SignalSource.WEBSITE,
                                        category=category,
                                        payload={"markdown": getattr(result, "markdown", "")},
                                        url=url,
                                    )
                                )
                                break  # first successful path for this category is enough
                        except Exception as exc:  # noqa: BLE001
                            errors.append(f"{category}:{path}: {exc}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"crawl4ai_init: {exc}")

        return CollectorResult(
            company_domain=company_domain,
            source=SignalSource.WEBSITE,
            signals=signals,
            is_live=True,
            errors=errors,
        )

