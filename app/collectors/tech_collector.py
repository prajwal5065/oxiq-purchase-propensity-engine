"""Tech Collector - uses Wappalyzer to fingerprint a company's frameworks,
cloud providers, analytics, CRM, marketing tools, and databases.
"""
from app.collectors.base import BaseCollector
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.signal import SignalSource
from app.schemas.signal import CollectorResult, CollectorStatus, RawSignal

logger = get_logger(__name__)

RELEVANT_CATEGORIES = {
    "Web frameworks",
    "JavaScript frameworks",
    "PaaS",
    "IaaS",
    "Analytics",
    "CRM",
    "Marketing automation",
    "Databases",
}


class TechCollector(BaseCollector):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def collect(self, company_domain: str) -> CollectorResult:
        if not self.settings.enable_live_tech_detection:
            logger.info("tech_collector.stub_mode", domain=company_domain)
            return CollectorResult(
                company_domain=company_domain,
                source=SignalSource.TECH,
                signals=[],
                is_live=False,
                errors=["Live tech detection disabled (ENABLE_LIVE_TECH_DETECTION=false) - stub mode"],
                status=CollectorStatus.NOT_CONFIGURED,
            )

        signals: list[RawSignal] = []
        errors: list[str] = []
        try:
            from Wappalyzer import Wappalyzer, WebPage  # imported lazily, optional heavy dep

            wappalyzer = Wappalyzer.latest()
            webpage = WebPage.new_from_url(f"https://{company_domain}")
            detected = wappalyzer.analyze_with_categories(webpage)

            for tech_name, meta in detected.items():
                categories = set(meta.get("categories", []))
                if not RELEVANT_CATEGORIES or categories & RELEVANT_CATEGORIES:
                    signals.append(
                        RawSignal(
                            source=SignalSource.TECH,
                            category=",".join(sorted(categories)) or "uncategorized",
                            payload={"technology": tech_name},
                            url=f"https://{company_domain}",
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"wappalyzer: {exc}")

        return CollectorResult(
            company_domain=company_domain,
            source=SignalSource.TECH,
            signals=signals,
            is_live=True,
            errors=errors,
        )
