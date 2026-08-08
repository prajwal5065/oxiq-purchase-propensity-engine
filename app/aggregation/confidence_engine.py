"""Confidence Engine (Stage 9).

Replaces a bare "0%" or "92%" with a factor-by-factor explanation of what's
driving the number, so a salesperson can tell "we're not confident because
almost nothing was collected" apart from "we're not confident because what
we collected disagreed with itself."

Weights are documented here rather than buried in a formula - if the
weighting ever needs tuning, this is the one place to look.
"""
from app.schemas.aggregation import EvidenceCoverageSummary
from app.schemas.explanation import ConfidenceExplanation, ConfidenceFactor
from app.schemas.signal import CollectorResult, CollectorStatus

# Roughly how much evidence a well-covered analysis should turn up. Not a
# hard requirement - just the denominator the "evidence count" factor
# saturates against, so 15+ pieces of evidence reads as "plenty" rather
# than needing an arbitrarily larger number to hit 1.0.
EXPECTED_EVIDENCE_COUNT = 15

_FACTOR_WEIGHTS: dict[str, float] = {
    "evidence_coverage": 0.20,
    "collector_success": 0.15,
    "source_diversity": 0.15,
    "source_reliability": 0.20,
    "evidence_freshness": 0.15,
    "signal_strength": 0.15,
}

HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.4


class ConfidenceEngine:
    def explain(
        self,
        coverage_summary: EvidenceCoverageSummary,
        collector_results: list[CollectorResult],
        total_evidence: int,
    ) -> ConfidenceExplanation:
        factors = self._build_factors(coverage_summary, collector_results, total_evidence)
        overall = round(sum(f.value * f.weight for f in factors), 2)
        level = self._level(overall)

        return ConfidenceExplanation(
            overall_confidence=overall,
            level=level,
            factors=factors,
            summary=self._summarize(level, overall, factors),
        )

    def _build_factors(
        self,
        coverage_summary: EvidenceCoverageSummary,
        collector_results: list[CollectorResult],
        total_evidence: int,
    ) -> list[ConfidenceFactor]:
        evidence_count_value = round(min(total_evidence / EXPECTED_EVIDENCE_COUNT, 1.0), 2)
        collector_success_value = (
            round(
                sum(1 for r in collector_results if r.resolved_status == CollectorStatus.SUCCESS)
                / len(collector_results),
                2,
            )
            if collector_results
            else 0.0
        )
        avg_freshness = (
            round(sum(g.freshness for g in coverage_summary.category_groups) / len(coverage_summary.category_groups), 2)
            if coverage_summary.category_groups
            else 0.0
        )
        avg_strength = (
            round(sum(g.strength for g in coverage_summary.category_groups) / len(coverage_summary.category_groups), 2)
            if coverage_summary.category_groups
            else 0.0
        )

        return [
            ConfidenceFactor(
                name="evidence_coverage",
                value=coverage_summary.overall_coverage,
                weight=_FACTOR_WEIGHTS["evidence_coverage"],
                description="Fraction of collectors that returned live, usable signals",
            ),
            ConfidenceFactor(
                name="collector_success",
                value=collector_success_value,
                weight=_FACTOR_WEIGHTS["collector_success"],
                description="Fraction of collectors that completed without error",
            ),
            ConfidenceFactor(
                name="source_diversity",
                # reuse evidence_count as a proxy floor, but diversity specifically
                # cares about how many *different* categories contributed evidence
                value=round(min(len(coverage_summary.category_groups) / 4, 1.0), 2),
                weight=_FACTOR_WEIGHTS["source_diversity"],
                description="How many distinct evidence categories were found, not just one narrow source",
            ),
            ConfidenceFactor(
                name="source_reliability",
                value=coverage_summary.overall_confidence,
                weight=_FACTOR_WEIGHTS["source_reliability"],
                description="Mean extraction confidence across all accepted evidence",
            ),
            ConfidenceFactor(
                name="evidence_freshness",
                value=avg_freshness,
                weight=_FACTOR_WEIGHTS["evidence_freshness"],
                description="How recent the underlying evidence is, on average",
            ),
            ConfidenceFactor(
                name="signal_strength",
                value=avg_strength,
                weight=_FACTOR_WEIGHTS["signal_strength"],
                description="Composite confidence/freshness/volume strength across evidence groups",
            ),
        ] + [
            ConfidenceFactor(
                name="evidence_count",
                value=evidence_count_value,
                weight=0.0,  # informational only - already implicitly captured via coverage/diversity/strength
                description=f"{total_evidence} evidence items accepted (soft target: {EXPECTED_EVIDENCE_COUNT})",
            )
        ]

    @staticmethod
    def _level(overall: float) -> str:
        if overall >= HIGH_THRESHOLD:
            return "high"
        if overall >= MEDIUM_THRESHOLD:
            return "medium"
        return "low"

    @staticmethod
    def _summarize(level: str, overall: float, factors: list[ConfidenceFactor]) -> str:
        weighted = [f for f in factors if f.weight > 0]
        weakest = min(weighted, key=lambda f: f.value * f.weight) if weighted else None
        strongest = max(weighted, key=lambda f: f.value * f.weight) if weighted else None

        parts = [f"Confidence is {level} ({overall:.0%})."]
        if strongest:
            parts.append(f"Strongest factor: {strongest.name.replace('_', ' ')} ({strongest.value:.0%}).")
        if weakest and weakest is not strongest:
            parts.append(f"Weakest factor: {weakest.name.replace('_', ' ')} ({weakest.value:.0%}).")
        return " ".join(parts)
