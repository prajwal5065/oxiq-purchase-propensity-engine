"""Disqualification Engine (Stage 8).

The Rule Engine decides *whether* to disqualify (that logic - configurable
thresholds - stays in app/rules/engine.py, unchanged). This module answers
the harder question: *why*, in a way that's honest about the difference
between "we looked and it's genuinely a poor fit" and "we couldn't collect
enough evidence to know." Those are never the same conclusion, and treating
missing data as a negative signal is exactly the failure mode this exists
to prevent (spec: "Do not claim that a company has low buying intent simply
because data collection failed").
"""
from app.schemas.explanation import (
    CollectorStatusReport,
    DisqualificationCategory,
    DisqualificationExplanation,
    EvidenceCoverage,
    PillarExplanation,
)
from app.schemas.score import PurchaseScoreResult
from app.schemas.signal import CollectorStatus

# An analysis with at least this much coverage and evidence volume is
# considered to have had a genuine look - if it's still disqualified past
# this bar, that's a conclusion about the company, not about data quality.
GENUINE_LOOK_COVERAGE_THRESHOLD = 0.5
GENUINE_LOOK_EVIDENCE_FLOOR = 3


class DisqualificationEngine:
    def explain(
        self,
        purchase_result: PurchaseScoreResult,
        coverage: EvidenceCoverage,
        pillar_explanations: list[PillarExplanation],
    ) -> DisqualificationExplanation:
        if not purchase_result.disqualified:
            return self._qualified(purchase_result, pillar_explanations)

        category = self._categorize(coverage)
        return self._disqualified(purchase_result, coverage, pillar_explanations, category)

    def _qualified(
        self, purchase_result: PurchaseScoreResult, pillar_explanations: list[PillarExplanation]
    ) -> DisqualificationExplanation:
        supporting = [
            contribution.label
            for pillar in sorted(pillar_explanations, key=lambda p: p.score, reverse=True)
            for contribution in pillar.positive_evidence[:2]
        ][:6]
        return DisqualificationExplanation(
            final_decision="qualified",
            category=DisqualificationCategory.NOT_DISQUALIFIED,
            primary_reason=f"Purchase score {purchase_result.purchase_score:.0f}/100 clears all disqualification thresholds.",
            secondary_reasons=[],
            disqualifying_rules_triggered=[],
            supporting_evidence=supporting,
            missing_evidence=[],
            data_quality_limitations=[],
            confidence=purchase_result.confidence,
            recommended_next_action="Proceed with standard outreach prioritization.",
        )

    def _categorize(self, coverage: EvidenceCoverage) -> DisqualificationCategory:
        """A. genuine negative evidence / B. insufficient evidence /
        C. collection failure / D. source unavailable - checked in the
        order that gives the most specific, most actionable answer first."""
        if coverage.sources_successful == 0 and coverage.sources_failed > 0:
            return DisqualificationCategory.COLLECTION_FAILURE

        if coverage.sources_successful == 0 and coverage.sources_not_configured == coverage.sources_discovered:
            return DisqualificationCategory.SOURCE_UNAVAILABLE

        had_genuine_look = (
            coverage.coverage_percentage >= GENUINE_LOOK_COVERAGE_THRESHOLD
            and coverage.evidence_items_accepted >= GENUINE_LOOK_EVIDENCE_FLOOR
        )
        if had_genuine_look:
            return DisqualificationCategory.GENUINE_NEGATIVE_EVIDENCE

        return DisqualificationCategory.INSUFFICIENT_EVIDENCE

    def _disqualified(
        self,
        purchase_result: PurchaseScoreResult,
        coverage: EvidenceCoverage,
        pillar_explanations: list[PillarExplanation],
        category: DisqualificationCategory,
    ) -> DisqualificationExplanation:
        final_decision = (
            "disqualified" if category == DisqualificationCategory.GENUINE_NEGATIVE_EVIDENCE else "insufficient_data"
        )

        supporting = [
            contribution.label
            for pillar in pillar_explanations
            for contribution in pillar.positive_evidence[:2]
        ][:6]
        missing_evidence = [
            f"No accepted evidence in category coverage for {report.source} ({report.status.value})"
            for report in coverage.collector_statuses
            if report.status != CollectorStatus.SUCCESS
        ]
        data_quality_limitations = [
            f"{report.source}: {'; '.join(report.errors)}" for report in coverage.collector_statuses if report.errors
        ]

        primary_reason, secondary_reasons, next_action = self._narrative(
            category, purchase_result, coverage
        )

        return DisqualificationExplanation(
            final_decision=final_decision,
            category=category,
            primary_reason=primary_reason,
            secondary_reasons=secondary_reasons,
            disqualifying_rules_triggered=(
                [purchase_result.disqualified_reason] if purchase_result.disqualified_reason else []
            ),
            supporting_evidence=supporting,
            missing_evidence=missing_evidence,
            data_quality_limitations=data_quality_limitations,
            confidence=purchase_result.confidence,
            recommended_next_action=next_action,
        )

    @staticmethod
    def _narrative(
        category: DisqualificationCategory,
        purchase_result: PurchaseScoreResult,
        coverage: EvidenceCoverage,
    ) -> tuple[str, list[str], str]:
        rule_reason = purchase_result.disqualified_reason or "a configured disqualification rule"

        if category == DisqualificationCategory.COLLECTION_FAILURE:
            return (
                "One or more collectors failed with a technical error before any evidence could be gathered.",
                [f"{rule_reason}", f"{coverage.sources_failed} of {coverage.sources_discovered} sources errored out"],
                "Retry the analysis - this is a data collection problem, not a business conclusion about the company.",
            )

        if category == DisqualificationCategory.SOURCE_UNAVAILABLE:
            return (
                "No live collectors are currently enabled, so no public evidence could be gathered.",
                [f"{rule_reason}", "All sources are running in stub mode (feature flags / API keys not configured)"],
                "Enable live collectors (search, crawl, or tech detection) and re-run before drawing any conclusion.",
            )

        if category == DisqualificationCategory.INSUFFICIENT_EVIDENCE:
            return (
                "Available public sources did not surface enough evidence to support a confident recommendation either way.",
                [
                    f"{rule_reason}",
                    f"Coverage was {coverage.coverage_percentage:.0%} with only "
                    f"{coverage.evidence_items_accepted} evidence items accepted",
                ],
                "Flag for manual review - absence of public signal is not the same as evidence of poor fit.",
            )

        # GENUINE_NEGATIVE_EVIDENCE
        return (
            f"Evidence was collected ({coverage.evidence_items_accepted} items, "
            f"{coverage.coverage_percentage:.0%} source coverage) and does not support purchase readiness: {rule_reason}",
            [rule_reason],
            "Deprioritize for active outreach; revisit if new funding, hiring, or product signals appear.",
        )
