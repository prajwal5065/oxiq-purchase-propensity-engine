"""Urgency Score - funding, hiring spike, expansion, acquisitions, new
products, cloud migration, AI adoption announcements.

Urgency is time-sensitive: a funding round announced this week matters far
more than one from three years ago. Matched evidence is weighted by
`time_decay.decay_weight` (age-bucketed) rather than counted flatly.
"""
from app.models.score import ScoreType
from app.scoring.base import BaseScoringAgent
from app.scoring.keyword_matcher import match_evidence
from app.scoring.time_decay import decay_weight
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
    "cloud migration",
    "migrating to the cloud",
    "adopts ai",
    "ai adoption",
    "partnership",
    "partners with",
    # Order/contract/deployment events - time-sensitive procurement or
    # rollout activity the original list didn't recognize unless it
    # happened to also say "expansion" or "partnership".
    "awarded contract",
    "wins contract",
    "places order",
    "deploys",
    "deployment of",
    "rolls out",
]

# Sum of decay weights at which urgency saturates to 100. ~3 fully-fresh
# signals (weight 1.0 each) is treated as maximally urgent.
MAX_EXPECTED_WEIGHT = 3.0


class UrgencyScoringAgent(BaseScoringAgent):
    score_type = ScoreType.URGENCY

    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        matched = match_evidence(evidence, KEYWORDS)
        weights = [decay_weight(e.published_at) for e in matched]
        total_weight = sum(weights)
        score = round(min(total_weight / MAX_EXPECTED_WEIGHT, 1.0) * 100, 1) if matched else 0.0

        reasons = [
            f"{e.signal_label} (decay weight {w:.1f}): {e.excerpt}"
            for e, w in zip(matched, weights, strict=True)
        ]

        return PillarScore(
            score_type=self.score_type,
            score=score,
            confidence=self._confidence_from_evidence(matched),
            reasons=reasons,
        )
