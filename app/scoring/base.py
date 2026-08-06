"""Base interface every Scoring Agent must implement.

Scoring agents ONLY calculate scores from evidence - business rules
(disqualifiers, confidence adjustments, industry priors) live in the Rule
Engine (phase 6, not yet built), never here.
"""
from abc import ABC, abstractmethod

from app.models.score import ScoreType
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore


class BaseScoringAgent(ABC):
    score_type: ScoreType

    @abstractmethod
    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        raise NotImplementedError

    def _confidence_from_evidence(self, matched: list[EvidenceItem]) -> float:
        """Simple, transparent default: mean confidence of matched evidence,
        0 when nothing matched (an agent should never claim confidence in
        the absence of supporting evidence)."""
        if not matched:
            return 0.0
        return round(sum(e.confidence for e in matched) / len(matched), 2)
