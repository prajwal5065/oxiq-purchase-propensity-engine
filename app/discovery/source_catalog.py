"""The full catalog of source types the evidence-first spec names (Stage
1/13), not just the ones we've built collectors for.

Keeping unimplemented sources (jobs boards, company/registry data, social
profiles) as explicit catalog entries - rather than simply absent from the
code - is the point: the spec's Stage 7 coverage view is supposed to show
"❌ LinkedIn ❌ Crunchbase" alongside real results, not silently omit them
because no one's built that collector yet. A gap you can see is a gap you
can prioritize; a gap that's just missing code looks like nothing was ever
planned there.

Adding a new collector is meant to be a one-line change here, not an edit
to the orchestrator - the orchestrator asks the SourceDiscoveryEngine what
to run, it doesn't hardcode a collector list itself.
"""
from collections.abc import Callable
from dataclasses import dataclass

from app.collectors.base import BaseCollector
from app.collectors.github_collector import GitHubCollector
from app.collectors.news_collector import NewsCollector
from app.collectors.search_collector import SearchCollector
from app.collectors.tech_collector import TechCollector
from app.collectors.website_collector import WebsiteCollector


@dataclass(frozen=True)
class SourceCatalogEntry:
    name: str
    label: str
    implemented: bool
    collector_factory: Callable[[], BaseCollector] | None = None


SOURCE_CATALOG: list[SourceCatalogEntry] = [
    SourceCatalogEntry("search", "Search", implemented=True, collector_factory=SearchCollector),
    SourceCatalogEntry("website", "Website / Careers / Blog", implemented=True, collector_factory=WebsiteCollector),
    SourceCatalogEntry("tech", "Technology Stack", implemented=True, collector_factory=TechCollector),
    SourceCatalogEntry("news", "News", implemented=True, collector_factory=NewsCollector),
    SourceCatalogEntry("github", "GitHub", implemented=True, collector_factory=GitHubCollector),
    SourceCatalogEntry("jobs", "Jobs (Greenhouse / Lever / Workday / LinkedIn Jobs)", implemented=False),
    SourceCatalogEntry("company", "Company Data (Crunchbase / OpenCorporates)", implemented=False),
    SourceCatalogEntry("social", "Social Profiles", implemented=False),
]
