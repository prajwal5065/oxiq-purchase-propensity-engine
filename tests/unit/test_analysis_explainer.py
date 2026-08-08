from app.aggregation.analysis_explainer import AnalysisExplainer
from app.models.score import ScoreType
from app.models.signal import SignalSource
from app.schemas.aggregation import EvidenceCoverageSummary, SignalGroup
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore, PurchaseScoreResult
from app.schemas.signal import CollectorResult, CollectorStatus, RawSignal


def test_headline_is_insufficient_data_when_disqualified_from_poor_coverage():
    purchase_result = PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=[
            PillarScore(score_type=t, score=0, confidence=0, reasons=[])
            for t in [
                ScoreType.NEED, ScoreType.URGENCY, ScoreType.CAPACITY,
                ScoreType.DIGITAL_MATURITY, ScoreType.ORG_READINESS, ScoreType.WINNABILITY,
            ]
        ],
        purchase_score=0.0,
        confidence=0.0,
        evidence_summary=[],
        disqualified=True,
        disqualified_reason="No pillar produced any matched evidence.",
    )
    collector_results = [
        CollectorResult(company_domain="acme.com", source=s, signals=[], is_live=False, errors=["stub"], status=CollectorStatus.NOT_CONFIGURED)
        for s in SignalSource
    ]
    coverage_summary = EvidenceCoverageSummary(
        company_domain="acme.com", total_evidence=0, sources_checked={}, category_groups=[],
        overall_coverage=0.0, overall_confidence=0.0,
    )

    explanation = AnalysisExplainer().explain(
        "acme.com", collector_results, evidence_items_extracted=0,
        normalized_evidence=[], coverage_summary=coverage_summary, purchase_result=purchase_result,
    )

    assert explanation.headline == "WHY WE CANNOT RECOMMEND THIS COMPANY"
    assert explanation.disqualification.category.value == "source_unavailable"


def test_headline_is_high_score_when_qualified_and_strong():
    pillar_scores = [PillarScore(score_type=t, score=90, confidence=0.9, reasons=[]) for t in ScoreType if t.value != "purchase_propensity"]
    purchase_result = PurchaseScoreResult(
        company_domain="acme.com", pillar_scores=pillar_scores, purchase_score=90.0, confidence=0.9,
        evidence_summary=[], disqualified=False, disqualified_reason=None,
    )
    coverage_summary = EvidenceCoverageSummary(
        company_domain="acme.com", total_evidence=10,
        sources_checked={"search": True, "website": True, "tech": True, "news": True},
        category_groups=[SignalGroup(category="hiring", signal_count=5, avg_confidence=0.9, freshness=0.9, strength=0.8)],
        overall_coverage=1.0, overall_confidence=0.9,
    )
    evidence = [EvidenceItem(signal_label="Hiring AI Engineers", excerpt="x", source="Careers Page", confidence=0.9)]
    collector_results = [
        CollectorResult(company_domain="acme.com", source=s, signals=[RawSignal(source=s, category="x", payload={})], is_live=True, errors=[])
        for s in SignalSource
    ]

    explanation = AnalysisExplainer().explain(
        "acme.com", collector_results, evidence_items_extracted=1,
        normalized_evidence=evidence, coverage_summary=coverage_summary, purchase_result=purchase_result,
    )

    assert explanation.headline == "WHY THIS COMPANY SCORED HIGH"
    assert explanation.disqualification.final_decision == "qualified"
    assert len(explanation.pillar_explanations) == len(pillar_scores)
