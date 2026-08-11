"""Decision Change Analyzer ('What Would Change Our Decision').

Turns the gaps already identified elsewhere (missing pillar signals,
failed/unconfigured sources, unresolved contradictions, absent timing
triggers) into a concrete, evidence-oriented list: not "we need more data"
in the abstract, but specifically which sources or signals would move the
needle, and in which direction. Nothing here invents a new judgment - every
factor is derived from data the rest of the pipeline already computed.
"""
from app.schemas.decision import (
    ChangeFactor,
    DecisionChangeAnalysis,
    DecisionPriority,
    DecisionRecommendation,
)
from app.schemas.explanation import EvidenceCoverage, PillarExplanation
from app.schemas.signal import CollectorStatus

MAX_FACTORS = 6


class DecisionChangeAnalyzer:
    def analyze(
        self,
        recommendation: DecisionRecommendation,
        coverage: EvidenceCoverage,
        pillar_explanations: list[PillarExplanation],
    ) -> DecisionChangeAnalysis:
        if recommendation.priority == DecisionPriority.INSUFFICIENT_DATA:
            factors = self._data_gap_factors(coverage)
            summary = "Resolving these data gaps is required before any priority decision can be made."
        elif recommendation.priority == DecisionPriority.LOW_PRIORITY and recommendation.decision_score == 0.0:
            # decision_score == 0.0 with LOW_PRIORITY is the DecisionEngine's
            # signature for "disqualified on the merits" (see decision_engine.py) -
            # a computed low score that happens to land at 0.0 is vanishingly
            # unlikely and, even then, still benefits from the same evidence-gap
            # framing below, so this branch only ever fires for the genuine case.
            factors = []
            summary = "Priority is fixed by disqualification and won't change without new evidence overturning it."
        else:
            factors = self._evidence_gap_factors(recommendation, pillar_explanations)
            summary = "The following would most likely move this company to a higher priority tier."

        return DecisionChangeAnalysis(factors=factors[:MAX_FACTORS], summary=summary)

    @staticmethod
    def _data_gap_factors(coverage: EvidenceCoverage) -> list[ChangeFactor]:
        factors: list[ChangeFactor] = []
        for report in coverage.collector_statuses:
            if report.status == CollectorStatus.SUCCESS:
                continue
            factors.append(
                ChangeFactor(
                    description=f"Get live results from the {report.source} source (currently {report.status.value}).",
                    evidence_needed=[f"A successful {report.source} collector run for this company"],
                )
            )
        for label in coverage.sources_not_implemented:
            factors.append(
                ChangeFactor(
                    description=f"Build a collector for {label}, currently not implemented.",
                    evidence_needed=[f"{label} evidence"],
                )
            )
        return factors

    @staticmethod
    def _evidence_gap_factors(
        recommendation: DecisionRecommendation, pillar_explanations: list[PillarExplanation]
    ) -> list[ChangeFactor]:
        factors: list[ChangeFactor] = []

        weakest_pillars = sorted(pillar_explanations, key=lambda p: p.score)[:3]
        for pillar in weakest_pillars:
            if not pillar.missing_expected_signals:
                continue
            factors.append(
                ChangeFactor(
                    description=(
                        f"Find evidence of {', '.join(pillar.missing_expected_signals[:2])} "
                        f"to raise {pillar.score_type.value}."
                    ),
                    evidence_needed=pillar.missing_expected_signals[:3],
                )
            )

        if recommendation.contradictions.has_contradictions:
            factors.append(
                ChangeFactor(
                    description="Resolve the contradictory evidence flagged above - it's currently discounting the score.",
                    evidence_needed=[f.theme for f in recommendation.contradictions.findings],
                )
            )

        if not recommendation.why_now.has_timing_trigger:
            factors.append(
                ChangeFactor(
                    description="A fresh timing trigger (funding, leadership change, expansion) would boost priority.",
                    evidence_needed=["A recent (within ~90 days) funding, leadership, or expansion signal"],
                )
            )

        if recommendation.buying_intent.level.value in ("none", "weak"):
            factors.append(
                ChangeFactor(
                    description="Stronger procurement-motion evidence (RFP, budget approval, pilot) would raise buying intent.",
                    evidence_needed=["Direct evidence of active vendor evaluation or budget allocation"],
                )
            )

        return factors
