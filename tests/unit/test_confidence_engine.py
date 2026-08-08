from app.aggregation.confidence_engine import ConfidenceEngine
from app.models.signal import SignalSource
from app.schemas.aggregation import EvidenceCoverageSummary, SignalGroup
from app.schemas.signal import CollectorResult, CollectorStatus, RawSignal


def make_result(source, status):
    signals = [RawSignal(source=source, category="x", payload={})] if status == CollectorStatus.SUCCESS else []
    return CollectorResult(
        company_domain="acme.com", source=source, signals=signals, is_live=True, errors=[], status=status
    )


def test_full_coverage_and_strength_gives_high_confidence():
    summary = EvidenceCoverageSummary(
        company_domain="acme.com",
        total_evidence=20,
        sources_checked={"search": True, "website": True, "tech": True, "news": True},
        category_groups=[
            SignalGroup(category="hiring", signal_count=5, avg_confidence=0.9, freshness=0.9, strength=0.8),
            SignalGroup(category="funding", signal_count=5, avg_confidence=0.9, freshness=0.9, strength=0.8),
            SignalGroup(category="technology", signal_count=5, avg_confidence=0.9, freshness=0.9, strength=0.8),
            SignalGroup(category="expansion", signal_count=5, avg_confidence=0.9, freshness=0.9, strength=0.8),
        ],
        overall_coverage=1.0,
        overall_confidence=0.9,
    )
    results = [make_result(s, CollectorStatus.SUCCESS) for s in SignalSource]
    explanation = ConfidenceEngine().explain(summary, results, total_evidence=20)

    assert explanation.level == "high"
    assert explanation.overall_confidence >= 0.7


def test_no_evidence_gives_low_confidence():
    summary = EvidenceCoverageSummary(
        company_domain="acme.com",
        total_evidence=0,
        sources_checked={},
        category_groups=[],
        overall_coverage=0.0,
        overall_confidence=0.0,
    )
    explanation = ConfidenceEngine().explain(summary, collector_results=[], total_evidence=0)
    assert explanation.level == "low"
    assert explanation.overall_confidence == 0.0


def test_factors_are_individually_returned_for_transparency():
    summary = EvidenceCoverageSummary(
        company_domain="acme.com",
        total_evidence=3,
        sources_checked={"search": True},
        category_groups=[SignalGroup(category="hiring", signal_count=3, avg_confidence=0.5, freshness=0.5, strength=0.3)],
        overall_coverage=0.25,
        overall_confidence=0.5,
    )
    explanation = ConfidenceEngine().explain(summary, collector_results=[], total_evidence=3)
    factor_names = {f.name for f in explanation.factors}
    assert {"evidence_coverage", "collector_success", "source_diversity", "source_reliability", "evidence_freshness", "signal_strength"} <= factor_names


def test_summary_mentions_level_and_percentage():
    summary = EvidenceCoverageSummary(
        company_domain="acme.com", total_evidence=0, sources_checked={}, category_groups=[],
        overall_coverage=0.0, overall_confidence=0.0,
    )
    explanation = ConfidenceEngine().explain(summary, collector_results=[], total_evidence=0)
    assert "low" in explanation.summary.lower()
