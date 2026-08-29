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
import re
from datetime import datetime

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
    ("builtwith", SignalSource.TECH),
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

        The same URL match also recovers the Tech/Jobs Collectors'
        structured payload fields (technology name/provider; job title/
        department/location/ATS provider/posting date) onto the matching
        EvidenceItem - see `_technology_fields_from`/`_job_fields_from`.
        This is the same trust boundary as the category inheritance above:
        only TECH/JOBS RawSignal payloads are ever read this way, so an
        unrelated collector's payload can never leak structured fields
        onto evidence it didn't produce.
        """
        url_to_jobs_category = {
            signal.url: signal.category
            for signal in raw_signals
            if signal.url and signal.category in _JOBS_SUBTYPE_CATEGORIES
        }
        url_to_tech_signal = {
            signal.url: signal for signal in raw_signals if signal.url and signal.source == SignalSource.TECH
        }
        url_to_jobs_signal = {
            signal.url: signal for signal in raw_signals if signal.url and signal.source == SignalSource.JOBS
        }
        url_to_profile_signal = {
            signal.url: signal
            for signal in raw_signals
            if signal.url and signal.source == SignalSource.COMPANY_PROFILE
        }

        seen: set[tuple[str, str]] = set()
        normalized: list[EvidenceItem] = []

        for item in items:
            dedupe_key = (item.source.strip().lower(), item.excerpt.strip().lower())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            item_url = str(item.url) if item.url else None
            inherited_category = url_to_jobs_category.get(item_url) if item_url else None
            update: dict = {
                "collector": item.collector or self._infer_collector(item.source),
                "category": item.category
                or inherited_category
                or self._infer_category(item.signal_label, item.excerpt),
            }

            tech_signal = url_to_tech_signal.get(item_url) if item_url else None
            if tech_signal is not None:
                update.update(self._technology_fields_from(tech_signal))

            jobs_signal = url_to_jobs_signal.get(item_url) if item_url else None
            if jobs_signal is not None:
                update.update(self._job_fields_from(jobs_signal))

            profile_signal = url_to_profile_signal.get(item_url) if item_url else None
            if profile_signal is not None:
                update.update(self._company_profile_fields_from(profile_signal))

            enriched = item.model_copy(update=update)
            normalized.append(enriched)

        return normalized

    @staticmethod
    def _technology_fields_from(signal: RawSignal) -> dict:
        """Structured technology_name/technology_provider from the Tech
        Collector's RawSignal.payload (see app/collectors/tech_collector.py) -
        never invented, only ever copied straight from what the collector
        already returned."""
        payload = signal.payload
        return {
            "technology_name": payload.get("technology"),
            "technology_provider": payload.get("provider"),
        }

    @staticmethod
    def _job_fields_from(signal: RawSignal) -> dict:
        """Structured job_* fields from the Jobs Collector's
        RawSignal.payload (see app/collectors/jobs_collector.py).
        `model_copy(update=...)` does not re-run Pydantic coercion, so
        `posted_at` (an ISO string in the payload, same as the collector
        wrote it) is parsed to a datetime here rather than left as a raw
        string."""
        payload = signal.payload
        posted_at = payload.get("posted_at")
        job_posting_date = None
        if posted_at:
            try:
                job_posting_date = datetime.fromisoformat(posted_at)
            except (TypeError, ValueError):
                job_posting_date = None
        return {
            "job_title": payload.get("title"),
            "job_department": payload.get("department"),
            "job_location": payload.get("location"),
            "job_ats_provider": payload.get("provider"),
            "job_posting_date": job_posting_date,
        }

    @staticmethod
    def _company_profile_fields_from(signal: RawSignal) -> dict:
        """Structured employee_count/founding_year from the Company Profile
        Collector's RawSignal.payload - either the homepage's schema.org
        JSON-LD (`numberOfEmployees`/`foundingDate`) or Wikidata
        (`employee_count`/`founding_date` - see
        app/collectors/company_profile_collector.py for both shapes). Both
        providers are normalized to the same plain int here so
        ContradictionDetector can compare "two sources' employee count" as
        one field regardless of which provider reported it or how."""
        payload = signal.payload
        raw_employees = payload.get("numberOfEmployees", payload.get("employee_count"))
        raw_founding = payload.get("foundingDate", payload.get("founding_date"))
        return {
            "employee_count": EvidenceNormalizer._parse_employee_count(raw_employees),
            "founding_year": EvidenceNormalizer._parse_founding_year(raw_founding),
        }

    @staticmethod
    def _parse_employee_count(raw: object) -> int | None:
        if raw is None:
            return None
        if isinstance(raw, dict):
            raw = raw.get("value") or raw.get("amount")
        if raw is None:
            return None
        try:
            # Wikidata quantity amounts arrive as strings like "+500".
            return int(float(str(raw).lstrip("+")))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_founding_year(raw: object) -> int | None:
        if raw is None:
            return None
        match = re.search(r"(\d{4})", str(raw))
        if not match:
            return None
        year = int(match.group(1))
        if 1600 <= year <= datetime.now().year:
            return year
        return None

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
