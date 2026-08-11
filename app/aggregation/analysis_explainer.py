"""Analysis Explainer.

The single entry point the orchestrator calls: given everything an analysis
run produced (collector results, evidence, pillar scores, the purchase
result), assembles the full AnalysisExplanation bundle from the four
focused engines below. Kept as a thin composition layer on purpose - each
engine is independently testable, this just wires them together and picks
the headline.
"""
from app.aggregation.confidence_engine import ConfidenceEngine
from app.aggregation.coverage_calculator import CoverageCalculator
from app.aggregation.disqualification_engine import DisqualificationEngine
from app.aggregation.pillar_explainer import PillarExplainer
from app.decision.decision_intelligence_engine import DecisionIntelligenceEngine
from app.schemas.aggregation import EvidenceCoverageSummary
from app.schemas.evidence import EvidenceItem
from app.schemas.explanation import AnalysisExplanation
from app.schemas.score import PurchaseScoreResult
from app.schemas.signal import CollectorResult

HIGH_SCORE_HEADLINE_THRESHOLD = 70.0


class AnalysisExplainer:
    def __init__(self) -> None:
        self.coverage_calculator = CoverageCalculator()
        self.confidence_engine = ConfidenceEngine()
        self.pillar_explainer = PillarExplainer()
        self.disqualification_engine = DisqualificationEngine()
        self.decision_intelligence_engine = DecisionIntelligenceEngine()

    def explain(
        self,
        company_domain: str,
        collector_results: list[CollectorResult],
        evidence_items_extracted: int,
        normalized_evidence: list[EvidenceItem],
        coverage_summary: EvidenceCoverageSummary,
        purchase_result: PurchaseScoreResult,
        sources_not_implemented: list[str] | None = None,
    ) -> AnalysisExplanation:
        coverage = self.coverage_calculator.calculate(
            collector_results=collector_results,
            evidence_items_extracted=evidence_items_extracted,
            evidence_items_accepted=len(normalized_evidence),
            sources_not_implemented=sources_not_implemented,
        )
        confidence_explanation = self.confidence_engine.explain(
            coverage_summary=coverage_summary,
            collector_results=collector_results,
            total_evidence=len(normalized_evidence),
        )
        pillar_explanations = [
            self.pillar_explainer.explain(pillar, normalized_evidence) for pillar in purchase_result.pillar_scores
        ]
        disqualification = self.disqualification_engine.explain(
            purchase_result=purchase_result, coverage=coverage, pillar_explanations=pillar_explanations
        )
        decision_intelligence = self.decision_intelligence_engine.build(
            evidence=normalized_evidence,
            coverage=coverage,
            purchase_result=purchase_result,
            disqualification=disqualification,
            pillar_explanations=pillar_explanations,
            overall_confidence=confidence_explanation.overall_confidence,
        )

        return AnalysisExplanation(
            company_domain=company_domain,
            headline=self._headline(purchase_result, disqualification.final_decision),
            evidence_coverage=coverage,
            confidence_explanation=confidence_explanation,
            pillar_explanations=pillar_explanations,
            disqualification=disqualification,
            decision_intelligence=decision_intelligence,
        )

    @staticmethod
    def _headline(purchase_result: PurchaseScoreResult, final_decision: str) -> str:
        if final_decision == "insufficient_data":
            return "WHY WE CANNOT RECOMMEND THIS COMPANY"
        if purchase_result.purchase_score >= HIGH_SCORE_HEADLINE_THRESHOLD:
            return "WHY THIS COMPANY SCORED HIGH"
        return "WHY THIS COMPANY SCORED LOW"
