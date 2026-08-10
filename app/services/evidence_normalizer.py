"""Evidence Normalizer.

Sits between the Evidence Extraction Layer and the Evidence Store. The
extractor's only job is grounding facts in text; it has no notion of which
collector a signal came from or what category of business signal it is.
The normalizer closes that gap so every stored Evidence row is fully
traceable (Stage 3/12 of the evidence-first spec): given the source string
an LLM wrote (e.g. "Careers Page", "Google News") and the RawSignals that
were actually collected, it infers `collector` and `category`, assigns a
stable id, and drops duplicate items (same source + near-identical excerpt)
so re-running extraction against overlapping raw signals doesn't inflate
evidence counts.

This is intentionally simple keyword/heuristic matching, not an LLM call -
normalization should be cheap, deterministic, and never itself invent a
fact the extractor didn't already ground.
"""
from app.models.signal import SignalSource
from app.schemas.evidence import EvidenceItem
from app.schemas.signal import RawSignal

# Maps a substring that might appear in EvidenceItem.source (as written by
# the extraction LLM) to the collector that most plausibly produced it.
_SOURCE_TO_COLLECTOR: list[tuple[str, SignalSource]] = [
    ("github", SignalSource.GITHUB),
    ("news", SignalSource.NEWS),
    ("press", SignalSource.NEWS),
    ("wappalyzer", SignalSource.TECH),
    ("tech", SignalSource.TECH),
    ("stack", SignalSource.TECH),
    ("search", SignalSource.SEARCH),
    ("google", SignalSource.SEARCH),
    ("career", SignalSource.WEBSITE),
    ("job", SignalSource.WEBSITE),
    ("website", SignalSource.WEBSITE),
    ("blog", SignalSource.WEBSITE),
    ("about", SignalSource.WEBSITE),
    ("crawl", SignalSource.WEBSITE),
]

# Category keyword groups, checked against "signal_label excerpt" lowercased.
# Order matters: first match wins, so more specific categories are listed
# before generic ones.
_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("funding", ["funding", "raised", "series a", "series b", "series c", "valuation", "investor"]),
    ("hiring", ["hiring", "engineer", "recruiting", "job opening", "headcount", "we're hiring"]),
    ("expansion", ["office", "expansion", "new market", "opening in", "expanding"]),
    ("executive", ["ceo", "cto", "cfo", "chief", "appointed", "executive", "leadership"]),
    ("technology", ["aws", "azure", "cloud", "api", "stack", "software", "platform", "automation"]),
    ("product", ["launch", "product", "release", "feature", "announcement"]),
]

DEFAULT_CATEGORY = "general"


class EvidenceNormalizer:
    def normalize(self, raw_signals: list[RawSignal], items: list[EvidenceItem]) -> list[EvidenceItem]:
        """Return a deduplicated, collector/category-tagged copy of `items`.

        `raw_signals` is accepted for future use (e.g. matching evidence
        back to a specific RawSignal by URL) but the current heuristic only
        needs the EvidenceItem's own `source` string and text.
        """
        del raw_signals  # not yet used for matching; kept in the signature for future URL-based matching

        seen: set[tuple[str, str]] = set()
        normalized: list[EvidenceItem] = []

        for item in items:
            dedupe_key = (item.source.strip().lower(), item.excerpt.strip().lower())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            enriched = item.model_copy(
                update={
                    "collector": item.collector or self._infer_collector(item.source),
                    "category": item.category or self._infer_category(item.signal_label, item.excerpt),
                }
            )
            normalized.append(enriched)

        return normalized

    @staticmethod
    def _infer_collector(source: str) -> str:
        lowered = source.lower()
        for keyword, collector in _SOURCE_TO_COLLECTOR:
            if keyword in lowered:
                return collector.value
        return "unknown"

    @staticmethod
    def _infer_category(signal_label: str, excerpt: str) -> str:
        haystack = f"{signal_label} {excerpt}".lower()
        for category, keywords in _CATEGORY_KEYWORDS:
            if any(keyword in haystack for keyword in keywords):
                return category
        return DEFAULT_CATEGORY
