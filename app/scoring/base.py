"""Base interface every Scoring Agent must implement.

Scoring agents ONLY calculate scores from evidence - business rules
(disqualifiers, confidence adjustments, industry priors) live in the Rule
Engine (phase 6, not yet built), never here.
"""
from abc import ABC, abstractmethod

from app.decision.evidence_confidence import EvidenceConfidenceEngine
from app.models.score import ScoreType
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore

_evidence_confidence_engine = EvidenceConfidenceEngine()


class BaseScoringAgent(ABC):
    score_type: ScoreType

    @abstractmethod
    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        raise NotImplementedError

    def _confidence_from_evidence(self, matched: list[EvidenceItem]) -> float:
        """Mean *composite* confidence of matched evidence - not the raw
        LLM extraction confidence alone, which search-derived evidence in
        particular tends to self-report near 1.0 regardless of how
        reliable the underlying source actually is.

        Delegates to EvidenceConfidenceEngine (already used by Decision
        Intelligence) so a pillar's confidence and the per-item confidence
        shown elsewhere in the report can never diverge: each item's
        composite blends extraction confidence with source reliability
        (collector tier - GitHub/Tech API facts outrank a search snippet)
        and freshness (a historical mention counts for less than a live
        signal). 0 when nothing matched - an agent should never claim
        confidence in the absence of supporting evidence.
        """
        if not matched:
            return 0.0
        composite_scores = _evidence_confidence_engine.score_batch(matched)
        return round(sum(s.composite_confidence for s in composite_scores) / len(composite_scores), 2)
