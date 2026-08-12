"""Source Reliability Engine (Decision Intelligence primitive).

Not every collector's evidence deserves equal trust. A signal read off a
company's own GitHub org or its live tech-stack detection is a structured,
directly-observed fact; a signal pulled from a news article or a keyword
search result has passed through an LLM's interpretation of prose first,
which is inherently less certain even when the extractor reports high
confidence for that one excerpt. This module assigns each collector a
reliability tier so Evidence Confidence, Buying Intent, and the Decision
Engine can all discount low-reliability sources consistently instead of
each reinventing its own notion of "how much do we trust this collector."

Tiers are a starting point, not a permanent ranking - if a source proves
more or less trustworthy in practice, this is the one place to retune it.
"""
from enum import StrEnum

from app.schemas.decision import SourceReliability
from app.schemas.evidence import EvidenceItem


class ReliabilityTier(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_TIER_WEIGHTS: dict[ReliabilityTier, float] = {
    ReliabilityTier.HIGH: 1.0,
    ReliabilityTier.MEDIUM: 0.65,
    ReliabilityTier.LOW: 0.4,
}

_COLLECTOR_TIERS: dict[str, tuple[ReliabilityTier, str]] = {
    "github": (
        ReliabilityTier.HIGH,
        "Structured API data (repos, commit activity) - directly observed, not inferred from prose.",
    ),
    "tech": (
        ReliabilityTier.HIGH,
        "Technology detection reads observable page fingerprints rather than interpreting free text.",
    ),
    "website": (
        ReliabilityTier.MEDIUM,
        "Scraped page content, then LLM-extracted - generally reliable but subject to extraction error.",
    ),
    "jobs": (
        ReliabilityTier.HIGH,
        "Structured ATS API data (Greenhouse/Lever job postings) - directly observed, not inferred from prose.",
    ),
    "news": (
        ReliabilityTier.MEDIUM,
        "Third-party reporting, LLM-extracted - accuracy depends on the publication and the extractor.",
    ),
    "search": (
        ReliabilityTier.LOW,
        "Search-result snippets are short and often out of context, raising misattribution risk.",
    ),
}

_DEFAULT_TIER: tuple[ReliabilityTier, str] = (
    ReliabilityTier.LOW,
    "Unrecognized or unattributed source - treated conservatively.",
)


class SourceReliabilityEngine:
    @staticmethod
    def tier_for_collector(collector: str | None) -> ReliabilityTier:
        tier, _rationale = _COLLECTOR_TIERS.get(collector or "unknown", _DEFAULT_TIER)
        return tier

    @staticmethod
    def weight_for_collector(collector: str | None) -> float:
        return _TIER_WEIGHTS[SourceReliabilityEngine.tier_for_collector(collector)]

    def summarize(self, items: list[EvidenceItem]) -> list[SourceReliability]:
        """One row per distinct collector present in the evidence, with a
        count - the aggregate view Decision Intelligence surfaces, as
        opposed to a per-item breakdown (which EvidenceConfidenceEngine
        already provides via `source_reliability` on each score)."""
        counts: dict[str, int] = {}
        for item in items:
            key = item.collector or "unknown"
            counts[key] = counts.get(key, 0) + 1

        results: list[SourceReliability] = []
        for collector, count in sorted(counts.items()):
            tier, rationale = _COLLECTOR_TIERS.get(collector, _DEFAULT_TIER)
            results.append(
                SourceReliability(
                    collector=collector,
                    tier=tier.value,
                    weight=_TIER_WEIGHTS[tier],
                    rationale=rationale,
                    evidence_count=count,
                )
            )
        return results
