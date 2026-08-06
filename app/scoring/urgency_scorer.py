"""Urgency Score - funding, hiring spike, expansion, acquisitions, new products."""
from app.models.score import ScoreType
from app.scoring.base import BaseScoringAgent
from app.scoring.keyword_matcher import match_evidence, weighted_score
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore

KEYWORDS = [
    "funding round",
    "raises",
    "series a",
    "series b",
    "series c",
    "hiring spike",
    "expansion",
    "new office",
    "acquisition",
    "acquires",
    "acquired",
    "product launch",
    "unveils",
]

MAX_EXPECTED_SIGNALS = 5


class UrgencyScoringAgent(BaseScoringAgent):
    score_type = ScoreType.URGENCY

    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        matched = match_evidence(evidence, KEYWORDS)
        return PillarScore(
            score_type=self.score_type,
            score=weighted_score(len(matched), MAX_EXPECTED_SIGNALS),
            confidence=self._confidence_from_evidence(matched),
            reasons=[f"{e.signal_label}: {e.excerpt}" for e in matched],
        )
