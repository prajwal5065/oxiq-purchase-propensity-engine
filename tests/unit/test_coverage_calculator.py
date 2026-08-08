from app.aggregation.coverage_calculator import CoverageCalculator
from app.models.signal import SignalSource
from app.schemas.signal import CollectorResult, CollectorStatus, RawSignal


def result(source, is_live, signals=None, errors=None, status=None):
    return CollectorResult(
        company_domain="acme.com",
        source=source,
        signals=signals or [],
        is_live=is_live,
        errors=errors or [],
        status=status,
    )


def test_all_successful_gives_full_coverage():
    results = [
        result(SignalSource.SEARCH, True, signals=[RawSignal(source=SignalSource.SEARCH, category="x", payload={})]),
        result(SignalSource.NEWS, True, signals=[RawSignal(source=SignalSource.NEWS, category="x", payload={})]),
    ]
    coverage = CoverageCalculator().calculate(results, evidence_items_extracted=5, evidence_items_accepted=4)
    assert coverage.sources_successful == 2
    assert coverage.coverage_percentage == 1.0
    assert coverage.sources_failed == 0


def test_distinguishes_not_configured_from_zero_results_from_failure():
    results = [
        result(SignalSource.SEARCH, False),  # stub mode -> NOT_CONFIGURED
        result(SignalSource.WEBSITE, True),  # ran live, nothing found -> NO_RESULTS
        result(SignalSource.TECH, True, errors=["wappalyzer: connection refused"]),  # ERROR
    ]
    coverage = CoverageCalculator().calculate(results, evidence_items_extracted=0, evidence_items_accepted=0)

    assert coverage.sources_not_configured == 1
    assert coverage.sources_zero_results == 1
    assert coverage.sources_failed == 1
    assert coverage.sources_successful == 0


def test_explicit_status_overrides_inference():
    results = [result(SignalSource.SEARCH, True, errors=["429 too many requests"], status=CollectorStatus.BLOCKED)]
    coverage = CoverageCalculator().calculate(results, evidence_items_extracted=0, evidence_items_accepted=0)
    assert coverage.collector_statuses[0].status == CollectorStatus.BLOCKED
    assert coverage.sources_failed == 1


def test_evidence_counts_pass_through_extracted_vs_accepted():
    coverage = CoverageCalculator().calculate([], evidence_items_extracted=10, evidence_items_accepted=7)
    assert coverage.evidence_items_extracted == 10
    assert coverage.evidence_items_accepted == 7


def test_empty_collector_results_gives_zero_coverage_not_error():
    coverage = CoverageCalculator().calculate([], evidence_items_extracted=0, evidence_items_accepted=0)
    assert coverage.sources_discovered == 0
    assert coverage.coverage_percentage == 0.0
