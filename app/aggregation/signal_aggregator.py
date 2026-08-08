"""Signal Aggregator.

Groups normalized evidence by category and computes, per group, how much
evidence exists, how confident it is, and how fresh it is - plus an overall
coverage view of which collectors actually returned usable signals. This is
the layer the spec's Stage 5 ("Signal Aggregator") and Stage 7 ("Evidence
Coverage") describe: it never touches raw text or crawls anything itself,
it only summarizes evidence that's already been extracted and normalized.

Kept deliberately separate from the Rule Engine and scoring agents - this
produces a *description* of the evidence ("here's what we have and how
strong it is"), not a decision. Scoring/disqualification still happens
downstream.
"""
from app.schemas.aggregation import EvidenceCoverageSummary, SignalGroup
from app.schemas.evidence import EvidenceItem
from app.schemas.signal import CollectorResult
from app.scoring.time_decay import decay_weight


class SignalAggregator:
    def aggregate(
        self,
        company_domain: str,
        evidence: list[EvidenceItem],
        collector_results: list[CollectorResult],
    ) -> EvidenceCoverageSummary:
        groups = self._group_by_category(evidence)
        sources_checked = self._sources_checked(collector_results)

        overall_coverage = (
            round(sum(1 for is_live in sources_checked.values() if is_live) / len(sources_checked), 2)
            if sources_checked
            else 0.0
        )
        overall_confidence = round(sum(e.confidence for e in evidence) / len(evidence), 2) if evidence else 0.0

        return EvidenceCoverageSummary(
            company_domain=company_domain,
            total_evidence=len(evidence),
            sources_checked=sources_checked,
            category_groups=groups,
            overall_coverage=overall_coverage,
            overall_confidence=overall_confidence,
        )

    @staticmethod
    def _group_by_category(evidence: list[EvidenceItem]) -> list[SignalGroup]:
        by_category: dict[str, list[EvidenceItem]] = {}
        for item in evidence:
            category = item.category or "general"
            by_category.setdefault(category, []).append(item)

        groups: list[SignalGroup] = []
        for category, items in sorted(by_category.items()):
            avg_confidence = round(sum(i.confidence for i in items) / len(items), 2)
            freshness = round(sum(decay_weight(i.published_at) for i in items) / len(items), 2)
            # Volume factor saturates at 3 signals - a 4th signal in the same
            # category shouldn't keep inflating "strength" indefinitely.
            volume_factor = min(len(items) / 3, 1.0)
            strength = round(avg_confidence * freshness * volume_factor, 2)
            groups.append(
                SignalGroup(
                    category=category,
                    signal_count=len(items),
                    avg_confidence=avg_confidence,
                    freshness=freshness,
                    strength=strength,
                )
            )
        return groups

    @staticmethod
    def _sources_checked(collector_results: list[CollectorResult]) -> dict[str, bool]:
        """A source counts as "checked" (True) only if it ran live and came
        back with at least one signal and no errors - matching the spec's
        distinction between a collector that's disabled/stubbed (❌) and one
        that ran but genuinely found nothing (also worth flagging, not
        hidden as a silent success)."""
        return {
            result.source.value: bool(result.is_live and result.signals and not result.errors)
            for result in collector_results
        }
