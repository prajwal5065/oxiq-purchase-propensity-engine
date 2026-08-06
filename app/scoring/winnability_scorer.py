"""Winnability Score - public contact channels, partnerships, vendor
friendliness, technology adoption.
"""
from app.models.score import ScoreType
from app.scoring.base import BaseScoringAgent
from app.scoring.keyword_matcher import match_evidence, weighted_score
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore

KEYWORDS = [
    "contact us",
    "request a demo",
    "partner program",
    "partnership",
    "integration marketplace",
    "vendor",
    "procurement",
    "rfp",
    "open to new tools",
]

MAX_EXPECTED_SIGNALS = 3


class WinnabilityScoringAgent(BaseScoringAgent):
    score_type = ScoreType.WINNABILITY

    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        matched = match_evidence(evidence, KEYWORDS)
        return PillarScore(
            score_type=self.score_type,
            score=weighted_score(len(matched), MAX_EXPECTED_SIGNALS),
            confidence=self._confidence_from_evidence(matched),
            reasons=[f"{e.signal_label}: {e.excerpt}" for e in matched],
        )
