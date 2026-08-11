"""Evidence Confidence Engine (Decision Intelligence primitive).

Composes three independent signals into one number per evidence item:
  - extraction confidence (how sure the LLM was about this specific excerpt)
  - source reliability (how much we trust this collector's evidence in general)
  - freshness (how recent the underlying fact is)

This is deliberately a *different* number from `Evidence.confidence` (the
raw extraction confidence stored on the row) and from the pillar-level
ConfidenceEngine (which explains the whole analysis, not one item). Buying
Intent, Contradiction Detection, and the Decision Engine all benefit from
being able to rank individual pieces of evidence against each other, and
extraction confidence alone isn't a fair ranking - a highly-confident
extraction from an unreliable source shouldn't outrank a moderately-
confident one from GitHub's API.
"""
from app.decision.freshness import FreshnessEngine
from app.decision.source_reliability import SourceReliabilityEngine
from app.schemas.decision import EvidenceConfidenceScore
from app.schemas.evidence import EvidenceItem

# Weights documented here, same pattern as ConfidenceEngine's _FACTOR_WEIGHTS -
# extraction confidence still dominates (it's the most direct signal about
# this specific excerpt), reliability and freshness adjust it.
_EXTRACTION_WEIGHT = 0.5
_RELIABILITY_WEIGHT = 0.3
_FRESHNESS_WEIGHT = 0.2


class EvidenceConfidenceEngine:
    def __init__(self, freshness_engine: FreshnessEngine | None = None) -> None:
        self.freshness_engine = freshness_engine or FreshnessEngine()

    def score(self, item: EvidenceItem) -> EvidenceConfidenceScore:
        freshness = self.freshness_engine.assess(item)
        reliability_weight = SourceReliabilityEngine.weight_for_collector(item.collector)

        composite = round(
            item.confidence * _EXTRACTION_WEIGHT
            + reliability_weight * _RELIABILITY_WEIGHT
            + freshness.weight * _FRESHNESS_WEIGHT,
            2,
        )

        return EvidenceConfidenceScore(
            evidence_id=item.id,
            label=item.signal_label,
            source=item.source,
            collector=item.collector,
            extraction_confidence=item.confidence,
            source_reliability=reliability_weight,
            freshness_weight=freshness.weight,
            composite_confidence=composite,
        )

    def score_batch(self, items: list[EvidenceItem]) -> list[EvidenceConfidenceScore]:
        return sorted((self.score(item) for item in items), key=lambda s: s.composite_confidence, reverse=True)
