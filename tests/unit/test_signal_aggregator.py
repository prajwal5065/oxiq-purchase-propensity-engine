from app.aggregation.signal_aggregator import SignalAggregator
from app.models.signal import SignalSource
from app.schemas.evidence import EvidenceItem
from app.schemas.signal import CollectorResult, RawSignal


def make_evidence(category: str, confidence: float = 0.8) -> EvidenceItem:
    return EvidenceItem(
        signal_label="x", excerpt="y", source="Careers Page", confidence=confidence, category=category
    )


def make_collector_result(source: SignalSource, is_live: bool, has_signal: bool, has_error: bool) -> CollectorResult:
    signals = [RawSignal(source=source, category="test", payload={})] if has_signal else []
    errors = ["boom"] if has_error else []
    return CollectorResult(company_domain="acme.com", source=source, signals=signals, is_live=is_live, errors=errors)


def test_aggregate_groups_evidence_by_category():
    evidence = [make_evidence("hiring"), make_evidence("hiring"), make_evidence("funding")]
    summary = SignalAggregator().aggregate("acme.com", evidence, collector_results=[])

    by_category = {g.category: g for g in summary.category_groups}
    assert by_category["hiring"].signal_count == 2
    assert by_category["funding"].signal_count == 1
    assert summary.total_evidence == 3


def test_aggregate_overall_confidence_is_mean_of_evidence():
    evidence = [make_evidence("hiring", confidence=1.0), make_evidence("hiring", confidence=0.5)]
    summary = SignalAggregator().aggregate("acme.com", evidence, collector_results=[])
    assert summary.overall_confidence == 0.75


def test_aggregate_handles_empty_evidence():
    summary = SignalAggregator().aggregate("acme.com", evidence=[], collector_results=[])
    assert summary.total_evidence == 0
    assert summary.overall_confidence == 0.0
    assert summary.category_groups == []


def test_sources_checked_true_only_when_live_with_signals_and_no_errors():
    results = [
        make_collector_result(SignalSource.NEWS, is_live=True, has_signal=True, has_error=False),
        make_collector_result(SignalSource.TECH, is_live=True, has_signal=False, has_error=False),
        make_collector_result(SignalSource.WEBSITE, is_live=True, has_signal=True, has_error=True),
        make_collector_result(SignalSource.SEARCH, is_live=False, has_signal=True, has_error=False),
    ]
    summary = SignalAggregator().aggregate("acme.com", evidence=[], collector_results=results)

    assert summary.sources_checked["news"] is True
    assert summary.sources_checked["tech"] is False
    assert summary.sources_checked["website"] is False
    assert summary.sources_checked["search"] is False


def test_overall_coverage_is_fraction_of_sources_that_checked_out():
    results = [
        make_collector_result(SignalSource.NEWS, is_live=True, has_signal=True, has_error=False),
        make_collector_result(SignalSource.TECH, is_live=False, has_signal=False, has_error=False),
    ]
    summary = SignalAggregator().aggregate("acme.com", evidence=[], collector_results=results)
    assert summary.overall_coverage == 0.5
