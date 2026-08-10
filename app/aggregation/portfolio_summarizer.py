"""Portfolio Summarizer.

Rolls up every company's latest AnalysisExplanation into portfolio-wide
counts and averages for the dashboard. Deliberately a pure function over
data the repository already fetched (purchase score + explanation payload
per company) rather than doing this aggregation in SQL - JSON field access
inside a query isn't portable between SQLite (tests) and Postgres
(production), and this mirrors how SignalAggregator/ConfidenceEngine
already aggregate in Python rather than in the database.
"""
from app.schemas.dashboard import DashboardSummary, DecisionCounts, DisqualificationCategoryCounts

HIGH_PRIORITY_SCORE_THRESHOLD = 70.0


class PortfolioSummarizer:
    def summarize(
        self,
        total_companies: int,
        rows: list[tuple[float | None, dict | None]],
    ) -> DashboardSummary:
        """`rows` is (latest_purchase_score, latest_explanation_payload) per
        company - a company with no completed analysis yet contributes
        (None, None) and is excluded from averages/decision counts, but
        still counts toward `total_companies`."""
        analyzed = [(score, payload) for score, payload in rows if payload is not None]

        decision_counts = DecisionCounts()
        category_counts = DisqualificationCategoryCounts()
        high_priority = 0
        confidences: list[float] = []
        coverages: list[float] = []
        scores: list[float] = []

        for score, payload in analyzed:
            disqualification = payload.get("disqualification", {})
            final_decision = disqualification.get("final_decision", "insufficient_data")
            category = disqualification.get("category", "insufficient_evidence")

            if hasattr(decision_counts, final_decision):
                setattr(decision_counts, final_decision, getattr(decision_counts, final_decision) + 1)
            if hasattr(category_counts, category):
                setattr(category_counts, category, getattr(category_counts, category) + 1)

            confidence_explanation = payload.get("confidence_explanation", {})
            if "overall_confidence" in confidence_explanation:
                confidences.append(confidence_explanation["overall_confidence"])

            coverage = payload.get("evidence_coverage", {})
            if "coverage_percentage" in coverage:
                coverages.append(coverage["coverage_percentage"])

            if score is not None:
                scores.append(score)
                if final_decision == "qualified" and score >= HIGH_PRIORITY_SCORE_THRESHOLD:
                    high_priority += 1

        return DashboardSummary(
            total_companies=total_companies,
            analyzed_companies=len(analyzed),
            by_decision=decision_counts,
            by_disqualification_category=category_counts,
            avg_confidence=round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
            avg_coverage=round(sum(coverages) / len(coverages), 2) if coverages else 0.0,
            avg_purchase_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
            high_priority_count=high_priority,
        )
