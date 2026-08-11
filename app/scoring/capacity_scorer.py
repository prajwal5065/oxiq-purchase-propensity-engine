"""Capacity Score - can this company actually afford/support a purchase?

Deliberately global and source-agnostic: relies only on public signals
that can come from any country or evidence source (search, website, news).
Region-specific data sources (e.g. an India-specific MCA/GST collector)
are explicitly out of scope here - if one is added later, it should feed
this scorer through the same `EvidenceItem` interface, not require scorer
changes.

Signals used:
- Company size (employees / headcount)
- Estimated or reported revenue
- Funding history
- Hiring trends
- Office / geographic expansion
- Technology investment
- Public financial reports (for public companies)
"""
from app.models.score import ScoreType
from app.scoring.base import BaseScoringAgent
from app.scoring.keyword_matcher import match_evidence, weighted_score
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore

KEYWORDS = [
    "employees",
    "headcount",
    "employee count",
    "company size",
    "team of",
    "industry",
    "headquartered",
    "revenue",
    "annual recurring revenue",
    "arr",
    "enterprise customer",
    "fortune 500",
    "raised $",
    "funding round",
    "valuation",
    "hiring trend",
    "growing team",
    "new office",
    "expands to",
    "expansion into",
    "quarterly earnings",
    "annual report",
    "10-k",
    "publicly traded",
    "market capitalization",
    "technology investment",
    "invests in",
]

MAX_EXPECTED_SIGNALS = 4


class CapacityScoringAgent(BaseScoringAgent):
    score_type = ScoreType.CAPACITY

    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        matched = match_evidence(evidence, KEYWORDS)
        return PillarScore(
            score_type=self.score_type,
            score=weighted_score(len(matched), MAX_EXPECTED_SIGNALS),
            confidence=self._confidence_from_evidence(matched),
            reasons=[f"{e.signal_label}: {e.excerpt}" for e in matched],
        )
