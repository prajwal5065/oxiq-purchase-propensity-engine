"""Evidence Coverage Calculator (Stage 1/7).

Turns the raw list of CollectorResults plus before/after evidence counts
into the EvidenceCoverage breakdown the frontend needs to distinguish "no
evidence was found" from "source was unavailable" from "collector failed" -
three situations the rest of the system must never collapse into one.
"""
from app.schemas.explanation import CollectorStatusReport, EvidenceCoverage
from app.schemas.signal import CollectorResult, CollectorStatus


class CoverageCalculator:
    def calculate(
        self,
        collector_results: list[CollectorResult],
        evidence_items_extracted: int,
        evidence_items_accepted: int,
        sources_not_implemented: list[str] | None = None,
    ) -> EvidenceCoverage:
        statuses = [self._to_status_report(r) for r in collector_results]

        by_status = {status: 0 for status in CollectorStatus}
        for report in statuses:
            by_status[report.status] += 1

        sources_discovered = len(collector_results)
        sources_successful = by_status[CollectorStatus.SUCCESS]
        coverage_percentage = round(sources_successful / sources_discovered, 2) if sources_discovered else 0.0

        return EvidenceCoverage(
            sources_discovered=sources_discovered,
            sources_attempted=sources_discovered,  # the orchestrator always invokes every registered collector
            sources_successful=sources_successful,
            sources_failed=by_status[CollectorStatus.ERROR]
            + by_status[CollectorStatus.TIMEOUT]
            + by_status[CollectorStatus.BLOCKED],
            sources_zero_results=by_status[CollectorStatus.NO_RESULTS],
            sources_not_configured=by_status[CollectorStatus.NOT_CONFIGURED],
            evidence_items_extracted=evidence_items_extracted,
            evidence_items_accepted=evidence_items_accepted,
            coverage_percentage=coverage_percentage,
            collector_statuses=statuses,
            sources_not_implemented=sources_not_implemented or [],
        )

    @staticmethod
    def _to_status_report(result: CollectorResult) -> CollectorStatusReport:
        return CollectorStatusReport(
            source=result.source.value,
            status=result.resolved_status,
            is_live=result.is_live,
            signal_count=len(result.signals),
            errors=result.errors,
        )
