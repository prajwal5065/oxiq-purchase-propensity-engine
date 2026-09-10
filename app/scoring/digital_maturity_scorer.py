"""Digital Maturity Score - cloud, APIs, Kubernetes, React, AWS, Azure.

Two sources of signal, combined and deduplicated:
  1. Structured technology evidence (`technology_name`, set by
     EvidenceNormalizer from the Tech Collector's BuiltWith/Wappalyzer
     detections - see app/schemas/evidence.py) - the ground truth for
     "what's actually in their stack", independent of whether the exact
     detector-reported name happens to appear in KEYWORDS below.
  2. Narrative keyword matches against evidence text (news/careers copy
     mentioning cloud-native practices, digital transformation, etc.) -
     catches maturity signals that aren't a single named technology.

Scoring against (2) alone undercounts real technology evidence whenever a
detected tool's name isn't in KEYWORDS (e.g. "Segment", "Cloudflare") or is
phrased differently in the item's excerpt than in the detector's own
field - which is exactly what made this score visibly inconsistent with
what the Technology panel showed for the same company: the panel reads
`technology_name` directly, the old scorer never looked at it.
"""
from app.models.score import ScoreType
from app.scoring.base import BaseScoringAgent
from app.scoring.keyword_matcher import dedupe_events, freshness_weighted_count, match_evidence, weighted_score
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

# Raised from 5: structured technology evidence alone can easily surface
# more than 5 distinct technologies for a modern stack, and a saturation
# point calibrated only for narrative keyword mentions would cap the score
# well below what the collected technology evidence actually supports.
MAX_EXPECTED_SIGNALS = 8


def matched_evidence(evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    """The evidence this pillar credits, in the same order/logic the
    scorer itself uses - shared with PillarExplainer so the attribution
    breakdown can never drift from the real score (see that module's
    docstring for why that invariant matters)."""
    tech_evidence = [e for e in evidence if e.technology_name or e.category == "technology"]
    narrative_matched = match_evidence(evidence, KEYWORDS)
    seen_ids = {e.id for e in tech_evidence}
    combined = list(tech_evidence) + [e for e in narrative_matched if e.id not in seen_ids]
    return dedupe_events(combined)


class DigitalMaturityScoringAgent(BaseScoringAgent):
    score_type = ScoreType.DIGITAL_MATURITY

    async def score(self, company_domain: str, evidence: list[EvidenceItem]) -> PillarScore:
        matched = matched_evidence(evidence)

        # Count distinct named technologies, not raw evidence rows - three
        # articles all mentioning "AWS" is one signal (AWS), not three.
        # Structured detections aren't freshness-discounted the same way
        # narrative mentions are: a tech-fingerprint scan observes what's
        # live on the site *now*, so it isn't "old evidence" the way a
        # years-old news mention of a stack choice is.
        distinct_technologies = {e.technology_name for e in matched if e.technology_name}
        narrative_only = [e for e in matched if e.technology_name is None]
        signal_count = len(distinct_technologies) + freshness_weighted_count(narrative_only)

        reasons = [f"Technology detected: {name}" for name in sorted(distinct_technologies)] + [
            f"{e.signal_label}: {e.excerpt}" for e in narrative_only
        ]

        return PillarScore(
            score_type=self.score_type,
            score=weighted_score(signal_count, MAX_EXPECTED_SIGNALS),
            confidence=self._confidence_from_evidence(matched),
            reasons=reasons,
        )
