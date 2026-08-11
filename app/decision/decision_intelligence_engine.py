"""Decision Intelligence Engine.

Composition layer, mirroring AnalysisExplainer (app/aggregation/analysis_explainer.py):
wires the freshness, source-reliability, evidence-confidence, buying-intent,
contradiction, why-now, decision, and change-analysis engines together into
one DecisionIntelligence bundle. Each sub-engine stays independently
testable; this just orders the calls and passes each engine's output to
the next.
"""
from app.decision.buying_intent_engine import BuyingIntentEngine
from app.decision.contradiction_detector import ContradictionDetector
from app.decision.decision_change_analyzer import DecisionChangeAnalyzer
from app.decision.decision_engine import DecisionEngine
from app.decision.evidence_confidence import EvidenceConfidenceEngine
from app.decision.source_reliability import SourceReliabilityEngine
from app.decision.why_now_engine import WhyNowEngine
from app.schemas.decision import DecisionIntelligence
from app.schemas.evidence import EvidenceItem
from app.schemas.explanation import DisqualificationExplanation, EvidenceCoverage, PillarExplanation
from app.schemas.score import PurchaseScoreResult


class DecisionIntelligenceEngine:
    def __init__(self) -> None:
        self.evidence_confidence_engine = EvidenceConfidenceEngine()
        self.source_reliability_engine = SourceReliabilityEngine()
        self.buying_intent_engine = BuyingIntentEngine()
        self.contradiction_detector = ContradictionDetector()
        self.why_now_engine = WhyNowEngine()
        self.decision_engine = DecisionEngine()
        self.change_analyzer = DecisionChangeAnalyzer()

    def build(
        self,
        evidence: list[EvidenceItem],
        coverage: EvidenceCoverage,
        purchase_result: PurchaseScoreResult,
        disqualification: DisqualificationExplanation,
        pillar_explanations: list[PillarExplanation],
        overall_confidence: float,
    ) -> DecisionIntelligence:
        buying_intent = self.buying_intent_engine.assess(
            evidence=evidence,
            coverage_percentage=coverage.coverage_percentage,
            evidence_items_accepted=coverage.evidence_items_accepted,
        )
        contradictions = self.contradiction_detector.detect(evidence)
        why_now = self.why_now_engine.explain(evidence)

        recommendation = self.decision_engine.decide(
            purchase_result=purchase_result,
            disqualification=disqualification,
            buying_intent=buying_intent,
            contradictions=contradictions,
            why_now=why_now,
            overall_confidence=overall_confidence,
        )
        change_analysis = self.change_analyzer.analyze(
            recommendation=recommendation, coverage=coverage, pillar_explanations=pillar_explanations
        )

        return DecisionIntelligence(
            recommendation=recommendation,
            change_analysis=change_analysis,
            evidence_confidence=self.evidence_confidence_engine.score_batch(evidence),
            source_reliability=self.source_reliability_engine.summarize(evidence),
        )
