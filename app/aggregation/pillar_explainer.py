"""Pillar Explainer (Stage 3/4).

Attributes each pillar's score back to the specific evidence that produced
it, without requiring any change to the scoring agents themselves: it
recomputes the same keyword match each scorer already did (agents only
expose module-level KEYWORDS, not the matched evidence itself) and splits
the pillar's already-computed score across the matches that earned it.
This guarantees the attribution always sums back to the real score - there's
no separate "explanation math" that can drift from the actual scoring math.

Urgency is the one agent that doesn't split evenly (it weighs by recency),
so its contribution split mirrors that: fresher evidence gets a bigger
share of the credit, same as it does in the real score.
"""
from app.models.score import ScoreType
from app.scoring import (
    capacity_scorer,
    digital_maturity_scorer,
    need_scorer,
    org_readiness_scorer,
    urgency_scorer,
    winnability_scorer,
)
from app.scoring.keyword_matcher import match_evidence
from app.scoring.time_decay import decay_weight
from app.schemas.evidence import EvidenceItem
from app.schemas.explanation import PillarExplanation, ScoreContribution
from app.schemas.score import PillarScore

_PILLAR_KEYWORDS: dict[ScoreType, list[str]] = {
    ScoreType.NEED: need_scorer.KEYWORDS,
    ScoreType.URGENCY: urgency_scorer.KEYWORDS,
    ScoreType.CAPACITY: capacity_scorer.KEYWORDS,
    ScoreType.DIGITAL_MATURITY: digital_maturity_scorer.KEYWORDS,
    ScoreType.ORG_READINESS: org_readiness_scorer.KEYWORDS,
    ScoreType.WINNABILITY: winnability_scorer.KEYWORDS,
}

# How many of a pillar's unmatched keyword phrases to surface as "expected
# but not observed" - capped so this stays a quick scan, not a keyword dump.
MAX_MISSING_SIGNALS = 5


class PillarExplainer:
    def explain(self, pillar_score: PillarScore, evidence: list[EvidenceItem]) -> PillarExplanation:
        keywords = _PILLAR_KEYWORDS.get(pillar_score.score_type, [])
        if pillar_score.score_type == ScoreType.DIGITAL_MATURITY:
            # Digital Maturity credits structured technology evidence
            # (technology_name) in addition to narrative keywords - use the
            # scorer's own matching logic rather than the generic
            # keyword-only path below, or this explanation would drift
            # from the score it's supposed to explain. `keywords` (above)
            # is still needed for the missing-expected-signals check.
            matched = digital_maturity_scorer.matched_evidence(evidence)
        else:
            matched = match_evidence(evidence, keywords)

        contributions = self._build_contributions(pillar_score, matched)
        missing = self._missing_signals(keywords, matched)
        source_coverage = self._source_coverage(matched)

        return PillarExplanation(
            score_type=pillar_score.score_type,
            score=pillar_score.score,
            confidence=pillar_score.confidence,
            positive_evidence=contributions,
            negative_evidence=[],  # no scorer currently produces negative per-item signals; reserved for future rule-engine penalties
            missing_expected_signals=missing,
            source_coverage=source_coverage,
        )

    def _build_contributions(
        self, pillar_score: PillarScore, matched: list[EvidenceItem]
    ) -> list[ScoreContribution]:
        if not matched or pillar_score.score <= 0:
            return []

        if pillar_score.score_type == ScoreType.URGENCY:
            weights = [decay_weight(e.published_at) for e in matched]
        else:
            weights = [1.0] * len(matched)

        total_weight = sum(weights) or 1.0
        return [
            ScoreContribution(
                evidence_id=item.id,
                label=item.signal_label,
                excerpt=item.excerpt,
                source=item.source,
                points=round(pillar_score.score * (weight / total_weight), 1),
                direction="positive",
            )
            for item, weight in zip(matched, weights, strict=True)
        ]

    @staticmethod
    def _missing_signals(keywords: list[str], matched: list[EvidenceItem]) -> list[str]:
        matched_text = " ".join(f"{e.signal_label} {e.excerpt}".lower() for e in matched)
        unmatched = [k for k in keywords if k.lower() not in matched_text]
        return unmatched[:MAX_MISSING_SIGNALS]

    @staticmethod
    def _source_coverage(matched: list[EvidenceItem]) -> dict[str, int]:
        coverage: dict[str, int] = {}
        for item in matched:
            key = item.collector or "unknown"
            coverage[key] = coverage.get(key, 0) + 1
        return coverage
