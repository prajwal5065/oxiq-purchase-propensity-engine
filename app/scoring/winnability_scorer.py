"""Winnability Score - how likely are we to actually win this deal, based
only on public signals (no CRM/relationship data - that's out of scope for
a public intelligence engine).

Signals used:
- Technology compatibility (stack that integrates cleanly with our product)
- Company maturity (how established / stable the company is)
- Existing AI adoption (already comfortable buying/using AI tools)
- Decision-making indicators (visible procurement/vendor-evaluation process)
- Engineering capability (a team that can actually implement and adopt us)
- Industry fit (operates in a vertical our product is built for)
"""
from app.models.score import ScoreType
from app.scoring.base import BaseScoringAgent
from app.scoring.keyword_matcher import freshness_weighted_count, match_evidence, weighted_score
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore

KEYWORDS = [
    # technology compatibility
    "api integration",
    "rest api",
    "open api",
    "integrates with",
    "webhook",
    # company maturity
    "founded in",
    "established",
    "years in business",
    "publicly traded",
    "market leader",
    # existing AI adoption
    "uses ai",
    "ai-powered",
    "leverages machine learning",
    "generative ai",
    "adopted ai",
    # decision-making indicators
    "request for proposal",
    "rfp",
    "vendor evaluation",
    "procurement process",
    "buying committee",
    # engineering capability
    "engineering blog",
    "open source",
    "github.com",
    "engineering team",
    # industry fit / organizational sophistication - deliberately broad
    # rather than locked to "software company". The original list here
    # only recognized software/SaaS companies, so no other vertical could
    # ever score industry fit at all, regardless of evidence. Absent a
    # configured ICP, these signals proxy for "a large, professionally-run
    # buying organization" across any industry. If OxiQ's actual ICP is a
    # specific vertical (e.g. transit/fleet), prefer configuring that via
    # `industry_priors` in app/rules/default_rules.json - the mechanism
    # already exists for this and is more maintainable than keyword
    # hardcoding - rather than adding vertical-specific terms here.
    "software company",
    "saas",
    "technology company",
    "digital-first",
    "public company",
    "government agency",
    "regulated industry",
    "enterprise organization",
    "national operator",
    "multi-site operations",
]

MAX_EXPECTED_SIGNALS = 4


class WinnabilityScoringAgent(BaseScoringAgent):
    score_type = ScoreType.WINNABILITY

    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        matched = match_evidence(evidence, KEYWORDS)
        return PillarScore(
            score_type=self.score_type,
            score=weighted_score(freshness_weighted_count(matched), MAX_EXPECTED_SIGNALS),
            confidence=self._confidence_from_evidence(matched),
            reasons=[f"{e.signal_label}: {e.excerpt}" for e in matched],
        )
