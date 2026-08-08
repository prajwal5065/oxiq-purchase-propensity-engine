import pytest

from app.models.score import ScoreType
from app.aggregation.pillar_explainer import PillarExplainer
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore


def make_evidence(label, excerpt, collector="website", source="Careers Page"):
    return EvidenceItem(signal_label=label, excerpt=excerpt, source=source, confidence=0.8, collector=collector)


def test_contributions_sum_back_to_pillar_score():
    evidence = [
        make_evidence("Hiring AI Engineers", "we are hiring an ai engineer"),
        make_evidence("Automation initiative", "launched an automation project"),
    ]
    pillar_score = PillarScore(score_type=ScoreType.NEED, score=33.3, confidence=0.8, reasons=[])

    explanation = PillarExplainer().explain(pillar_score, evidence)

    assert len(explanation.positive_evidence) == 2
    assert sum(c.points for c in explanation.positive_evidence) == pytest.approx(33.3, abs=0.5)


def test_no_matches_gives_no_contributions():
    pillar_score = PillarScore(score_type=ScoreType.NEED, score=0.0, confidence=0.0, reasons=[])
    explanation = PillarExplainer().explain(pillar_score, evidence=[])
    assert explanation.positive_evidence == []


def test_missing_expected_signals_lists_unmatched_keywords():
    evidence = [make_evidence("Hiring AI Engineers", "we are hiring an ai engineer")]
    pillar_score = PillarScore(score_type=ScoreType.NEED, score=16.7, confidence=0.8, reasons=[])

    explanation = PillarExplainer().explain(pillar_score, evidence)

    assert "spreadsheet" in explanation.missing_expected_signals or len(explanation.missing_expected_signals) > 0


def test_source_coverage_counts_by_collector():
    evidence = [
        make_evidence("Hiring AI Engineers", "we are hiring an ai engineer", collector="website"),
        make_evidence("AI engineer job posting", "posted an ai engineer role", collector="search"),
    ]
    pillar_score = PillarScore(score_type=ScoreType.NEED, score=33.3, confidence=0.8, reasons=[])

    explanation = PillarExplainer().explain(pillar_score, evidence)

    assert explanation.source_coverage.get("website") == 1
    assert explanation.source_coverage.get("search") == 1


def test_urgency_pillar_weighs_contributions_by_recency():
    from datetime import UTC, datetime, timedelta

    fresh = make_evidence("Series B funding", "raised a series b round")
    fresh = fresh.model_copy(update={"published_at": datetime.now(UTC)})
    stale = make_evidence("Old acquisition", "acquires a competitor")
    stale = stale.model_copy(update={"published_at": datetime.now(UTC) - timedelta(days=900)})

    pillar_score = PillarScore(score_type=ScoreType.URGENCY, score=50.0, confidence=0.7, reasons=[])
    explanation = PillarExplainer().explain(pillar_score, [fresh, stale])

    points_by_label = {c.label: c.points for c in explanation.positive_evidence}
    assert points_by_label["Series B funding"] > points_by_label["Old acquisition"]
