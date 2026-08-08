"""Source Discovery Engine (Stage 1).

Formalizes "which sources exist for this analysis" as its own step,
upstream of collection, instead of the orchestrator hardcoding a fixed
collector list. Two things fall out of that:

1. Adding a collector is a one-line addition to SOURCE_CATALOG, not an
   orchestrator edit.
2. Sources named in the spec that nobody's built yet (jobs boards,
   company/registry data, social) become visible, trackable gaps instead
   of just... not existing anywhere in the code.

`discover()` takes `company_domain` and is async even though today's
catalog doesn't do any per-company filtering - every implemented source
runs for every company. That's a deliberate seam: real per-company
applicability (e.g. "no plausible GitHub account for this domain, don't
bother") belongs here when it's built, without another interface change
to the orchestrator.
"""
from dataclasses import dataclass

from app.collectors.base import BaseCollector
from app.discovery.source_catalog import SOURCE_CATALOG


@dataclass
class DiscoveredSource:
    name: str
    label: str
    implemented: bool


class SourceDiscoveryEngine:
    async def discover(self, company_domain: str) -> list[DiscoveredSource]:
        del company_domain  # not yet used for filtering - see module docstring
        return [
            DiscoveredSource(name=entry.name, label=entry.label, implemented=entry.implemented)
            for entry in SOURCE_CATALOG
        ]

    async def collectors_to_run(self, company_domain: str) -> list[BaseCollector]:
        discovered = await self.discover(company_domain)
        implemented_names = {d.name for d in discovered if d.implemented}
        return [
            entry.collector_factory()
            for entry in SOURCE_CATALOG
            if entry.name in implemented_names and entry.collector_factory is not None
        ]

    @staticmethod
    def not_implemented_labels(discovered: list[DiscoveredSource]) -> list[str]:
        return [d.label for d in discovered if not d.implemented]
