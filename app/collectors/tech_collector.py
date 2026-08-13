"""Tech Collector - uses Wappalyzer to fingerprint a company's frameworks,
cloud providers, analytics, CRM, marketing tools, and databases.
"""
import httpx

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
        self.builtwith_api_url = "https://api.builtwith.com/v23/api.json"

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
        
        # 1. Primary: BuiltWith
        if self.settings.builtwith_api_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        self.builtwith_api_url,
                        params={"KEY": self.settings.builtwith_api_key, "LOOKUP": company_domain}
                    )
                if response.status_code == 200:
                    data = response.json()
                    # Check for API-level errors in payload (e.g. quota exceeded)
                    api_errors = data.get("Errors")
                    if api_errors and len(api_errors) > 0:
                        errors.append(f"builtwith: API Error - {api_errors[0].get('Message', 'Unknown')}")
                    else:
                        results = data.get("Results", [])
                        if results:
                            paths = results[0].get("Result", {}).get("Paths", [])
                            technologies = paths[0].get("Technologies", []) if paths else []
                            
                            seen_tech = set()
                            for tech in technologies:
                                tech_name = tech.get("Name")
                                tech_tag = tech.get("Tag") or "uncategorized"
                                if tech_name and tech_name not in seen_tech:
                                    seen_tech.add(tech_name)
                                    signals.append(
                                        RawSignal(
                                            source=SignalSource.TECH,
                                            category=tech_tag,
                                            payload={"technology": tech_name, "provider": "builtwith"},
                                            url=f"https://{company_domain}",
                                        )
                                    )
                            if signals:
                                return CollectorResult(
                                    company_domain=company_domain,
                                    source=SignalSource.TECH,
                                    signals=signals,
                                    is_live=True,
                                    errors=errors,
                                )
                            else:
                                errors.append("builtwith: No technologies found")
                elif response.status_code == 429:
                    errors.append("builtwith: Quota exceeded or rate limited (429)")
                else:
                    errors.append(f"builtwith: HTTP {response.status_code}")
            except Exception as exc:
                errors.append(f"builtwith: {exc}")
        else:
            errors.append("builtwith: No API key configured")

        # 2. Fallback: Wappalyzer
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
                            payload={"technology": tech_name, "provider": "wappalyzer"},
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
