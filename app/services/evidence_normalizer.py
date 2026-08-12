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
    ("wikidata", SignalSource.COMPANY_PROFILE),
    ("company profile", SignalSource.COMPANY_PROFILE),
    ("company registry", SignalSource.COMPANY_PROFILE),
    ("schema.org", SignalSource.COMPANY_PROFILE),
    ("organization profile", SignalSource.COMPANY_PROFILE),
    ("wappalyzer", SignalSource.TECH),
    ("tech", SignalSource.TECH),
    ("stack", SignalSource.TECH),
    ("search", SignalSource.SEARCH),
    ("google", SignalSource.SEARCH),
    ("greenhouse", SignalSource.JOBS),
    ("lever", SignalSource.JOBS),
    ("job board", SignalSource.JOBS),
    ("jobs board", SignalSource.JOBS),
    ("job posting", SignalSource.JOBS),
    ("job listing", SignalSource.JOBS),
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
    (
        "company_profile",
        [
            "industry", "sector", "employee count", "company size", "founded in",
            "founding date", "headquartered", "naics", "sic code", "organization type",
        ],
    ),
    ("expansion", ["office", "expansion", "new market", "opening in", "expanding"]),
    ("executive", ["ceo", "cto", "cfo", "chief", "appointed", "executive", "leadership"]),
    ("technology", ["aws", "azure", "cloud", "api", "stack", "software", "platform", "automation"]),
    ("product", ["launch", "product", "release", "feature", "announcement"]),
]

DEFAULT_CATEGORY = "general"

# Category values the Jobs Collector itself assigns per-posting (see
# app/collectors/jobs_collector.py) - these ride on the RawSignal, not
# guessed from LLM-paraphrased excerpt text, so when a normalized item's
# URL matches the RawSignal that produced it, we trust that tag over the
# generic keyword heuristic below. Scoped to exactly these values (rather
# than trusting any RawSignal.category) so this can never silently change
# categorization for every other collector's evidence.
_JOBS_SUBTYPE_CATEGORIES = {
    "ai_ml_hiring",
    "engineering_hiring",
    "data_hiring",
    "cloud_devops_hiring",
    "security_hiring",
    "general_hiring",
}


class EvidenceNormalizer:
    def normalize(self, raw_signals: list[RawSignal], items: list[EvidenceItem]) -> list[EvidenceItem]:
        """Return a deduplicated, collector/category-tagged copy of `items`.

        `raw_signals` is used to recover the Jobs Collector's own hiring-
        category tag (by matching each item's URL back to the RawSignal
        that produced it) before falling back to keyword inference - see
        `_JOBS_SUBTYPE_CATEGORIES` above. For every other source this is a
        no-op: no RawSignal from another collector ever carries one of
        those category values.
        """
        url_to_jobs_category = {
            signal.url: signal.category
            for signal in raw_signals
            if signal.url and signal.category in _JOBS_SUBTYPE_CATEGORIES
        }

        seen: set[tuple[str, str]] = set()
        normalized: list[EvidenceItem] = []

        for item in items:
            dedupe_key = (item.source.strip().lower(), item.excerpt.strip().lower())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            inherited_category = url_to_jobs_category.get(str(item.url)) if item.url else None
            enriched = item.model_copy(
                update={
                    "collector": item.collector or self._infer_collector(item.source),
                    "category": item.category
                    or inherited_category
                    or self._infer_category(item.signal_label, item.excerpt),
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
