from app.aggregation.portfolio_summarizer import PortfolioSummarizer


def make_payload(final_decision: str, category: str, confidence=0.8, coverage=0.75):
    return {
        "disqualification": {"final_decision": final_decision, "category": category},
        "confidence_explanation": {"overall_confidence": confidence},
        "evidence_coverage": {"coverage_percentage": coverage},
    }


def test_counts_unanalyzed_companies_in_total_but_not_averages():
    rows = [(None, None), (90.0, make_payload("qualified", "not_disqualified"))]
    summary = PortfolioSummarizer().summarize(total_companies=2, rows=rows)

    assert summary.total_companies == 2
    assert summary.analyzed_companies == 1
    assert summary.avg_purchase_score == 90.0


def test_decision_counts_by_category():
    rows = [
        (90.0, make_payload("qualified", "not_disqualified")),
        (0.0, make_payload("disqualified", "genuine_negative_evidence")),
        (0.0, make_payload("insufficient_data", "source_unavailable")),
        (0.0, make_payload("insufficient_data", "collection_failure")),
    ]
    summary = PortfolioSummarizer().summarize(total_companies=4, rows=rows)

    assert summary.by_decision.qualified == 1
    assert summary.by_decision.disqualified == 1
    assert summary.by_decision.insufficient_data == 2
    assert summary.by_disqualification_category.genuine_negative_evidence == 1
    assert summary.by_disqualification_category.source_unavailable == 1
    assert summary.by_disqualification_category.collection_failure == 1


def test_high_priority_only_counts_qualified_above_threshold():
    rows = [
        (95.0, make_payload("qualified", "not_disqualified")),
        (50.0, make_payload("qualified", "not_disqualified")),  # qualified but below threshold
        (95.0, make_payload("disqualified", "genuine_negative_evidence")),  # high score but disqualified
    ]
    summary = PortfolioSummarizer().summarize(total_companies=3, rows=rows)
    assert summary.high_priority_count == 1


def test_avg_confidence_and_coverage_computed_across_analyzed_only():
    rows = [
        (80.0, make_payload("qualified", "not_disqualified", confidence=1.0, coverage=1.0)),
        (60.0, make_payload("qualified", "not_disqualified", confidence=0.5, coverage=0.5)),
    ]
    summary = PortfolioSummarizer().summarize(total_companies=2, rows=rows)
    assert summary.avg_confidence == 0.75
    assert summary.avg_coverage == 0.75


def test_empty_portfolio_gives_zeroed_summary_not_error():
    summary = PortfolioSummarizer().summarize(total_companies=0, rows=[])
    assert summary.total_companies == 0
    assert summary.analyzed_companies == 0
    assert summary.avg_confidence == 0.0
    assert summary.avg_purchase_score == 0.0


def test_all_companies_analyzed_but_none_completed_yet():
    rows = [(None, None), (None, None)]
    summary = PortfolioSummarizer().summarize(total_companies=2, rows=rows)
    assert summary.analyzed_companies == 0
    assert summary.total_companies == 2
