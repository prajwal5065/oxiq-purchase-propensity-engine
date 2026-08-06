"""Need Score - do they have our problem? Are manual workflows visible?
Are they investing in AI?
"""
from app.models.score import ScoreType
from app.scoring.base import BaseScoringAgent
from app.scoring.keyword_matcher import match_evidence, weighted_score
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore

KEYWORDS = [
    "manual process",
    "spreadsheet",
    "manual workflow",
    "hiring ai",
    "ai engineer",
    "machine learning engineer",
    "automation",
    "inefficient",
    "bottleneck",
    "data entry",
]

MAX_EXPECTED_SIGNALS = 6


class NeedScoringAgent(BaseScoringAgent):
    score_type = ScoreType.NEED

    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        matched = match_evidence(evidence, KEYWORDS)
        return PillarScore(
            score_type=self.score_type,
            score=weighted_score(len(matched), MAX_EXPECTED_SIGNALS),
            confidence=self._confidence_from_evidence(matched),
            reasons=[f"{e.signal_label}: {e.excerpt}" for e in matched],
        )
