"""Organization Readiness Score - CTO, AI leadership, engineering team,
innovation team.
"""
from app.models.score import ScoreType
from app.scoring.base import BaseScoringAgent
from app.scoring.keyword_matcher import match_evidence, weighted_score
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore

KEYWORDS = [
    "chief technology officer",
    "cto",
    "vp of engineering",
    "head of ai",
    "head of data",
    "innovation team",
    "engineering team",
    "director of engineering",
    "chief ai officer",
    # Organizational scale/build-out signals - the original list only
    # recognized named leadership titles, so a company visibly growing its
    # workforce (e.g. hundreds of open positions) never counted as an
    # org-readiness signal even though large-scale hiring is real evidence
    # an organization is being staffed up to execute.
    "dedicated team",
    "operations team",
    "project team",
    "center of excellence",
    "job vacancies",
    "open positions",
    "hiring across",
    "expanding workforce",
    "new department",
]

MAX_EXPECTED_SIGNALS = 3


class OrgReadinessScoringAgent(BaseScoringAgent):
    score_type = ScoreType.ORG_READINESS

    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        matched = match_evidence(evidence, KEYWORDS)
        return PillarScore(
            score_type=self.score_type,
            score=weighted_score(len(matched), MAX_EXPECTED_SIGNALS),
            confidence=self._confidence_from_evidence(matched),
            reasons=[f"{e.signal_label}: {e.excerpt}" for e in matched],
        )
