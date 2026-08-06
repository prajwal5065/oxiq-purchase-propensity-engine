"""News Collector - uses Google News RSS to find funding, acquisitions,
expansion, partnerships, product launches, and executive-change news.

Google News RSS requires no API key, so this collector is "live" by
default; it can still be disabled via ENABLE_LIVE_SEARCH-style flags if
outbound network access needs to be restricted in a given environment.
"""
from urllib.parse import quote

from app.collectors.base import BaseCollector
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.signal import SignalSource
from app.schemas.signal import CollectorResult, RawSignal

logger = get_logger(__name__)

NEWS_TOPICS = [
    ("funding", "{name} funding round OR raises"),
    ("acquisition", "{name} acquires OR acquisition"),
    ("expansion", "{name} expands OR opens new office"),
    ("partnership", "{name} partnership OR partners with"),
    ("product_launch", "{name} launches OR unveils"),
    ("executive_change", "{name} appoints OR names new CEO OR CTO"),
]


class NewsCollector(BaseCollector):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def collect(self, company_domain: str) -> CollectorResult:
        company_name = company_domain.split(".")[0]
        signals: list[RawSignal] = []
        errors: list[str] = []

        try:
            import feedparser

            for category, query_template in NEWS_TOPICS:
                query = query_template.format(name=company_name)
                url = f"{self.settings.google_news_rss_base}?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:5]:
                        signals.append(
                            RawSignal(
                                source=SignalSource.NEWS,
                                category=category,
                                payload={
                                    "title": entry.get("title"),
                                    "summary": entry.get("summary"),
                                    "published": entry.get("published"),
                                },
                                url=entry.get("link"),
                            )
                        )
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{category}: {exc}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"feedparser_init: {exc}")

        return CollectorResult(
            company_domain=company_domain,
            source=SignalSource.NEWS,
            signals=signals,
            is_live=True,
            errors=errors,
        )
