"""Digital Maturity Score - cloud, APIs, Kubernetes, React, AWS, Azure."""
from app.models.score import ScoreType
from app.scoring.base import BaseScoringAgent
from app.scoring.keyword_matcher import match_evidence, weighted_score
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore

KEYWORDS = [
    "kubernetes",
    "docker",
    "react",
    "aws",
    "azure",
    "google cloud",
    "gcp",
    "api",
    "microservices",
    "graphql",
    "terraform",
    "machine learning",
    "artificial intelligence",
    "generative ai",
    "cloud-native",
    # Technology-adoption signals that aren't tied to a specific software
    # stack - the original list only recognized named developer tooling,
    # so a company visibly modernizing (e.g. a fleet operator adopting EV/
    # telematics/IoT technology) never registered here at all.
    "digital transformation",
    "iot",
    "telematics",
    "real-time tracking",
    "connected vehicles",
    "data-driven",
    "smart technology",
    "technology platform",
    "electrification",
]

MAX_EXPECTED_SIGNALS = 5


class DigitalMaturityScoringAgent(BaseScoringAgent):
    score_type = ScoreType.DIGITAL_MATURITY

    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        matched = match_evidence(evidence, KEYWORDS)
        return PillarScore(
            score_type=self.score_type,
            score=weighted_score(len(matched), MAX_EXPECTED_SIGNALS),
            confidence=self._confidence_from_evidence(matched),
            reasons=[f"{e.signal_label}: {e.excerpt}" for e in matched],
        )
