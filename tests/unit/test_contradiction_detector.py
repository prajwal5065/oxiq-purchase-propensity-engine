from app.decision.contradiction_detector import ContradictionDetector
from app.schemas.evidence import EvidenceItem


def make_evidence(label, excerpt):
    return EvidenceItem(signal_label=label, excerpt=excerpt, source="News", confidence=0.8)


def test_no_contradiction_when_evidence_is_empty():
    report = ContradictionDetector().detect([])
    assert report.has_contradictions is False
    assert report.findings == []


def test_no_contradiction_when_only_positive_signals_present():
    evidence = [make_evidence("Hiring Spike", "the company announced a hiring spike this month")]
    report = ContradictionDetector().detect(evidence)
    assert report.has_contradictions is False


def test_detects_hiring_trajectory_contradiction():
    evidence = [
        make_evidence("Hiring Spike", "the company announced a hiring spike"),
        make_evidence("Layoffs", "the company also announced layoffs last week"),
    ]
    report = ContradictionDetector().detect(evidence)

    assert report.has_contradictions is True
    assert any(f.theme == "hiring_trajectory" for f in report.findings)


def test_detects_financial_trajectory_contradiction():
    evidence = [
        make_evidence("Series B", "the company closed a series b funding round"),
        make_evidence("Cost Cutting", "the company is undergoing aggressive cost-cutting"),
    ]
    report = ContradictionDetector().detect(evidence)

    assert any(f.theme == "financial_trajectory" for f in report.findings)


def test_findings_cite_both_pieces_of_evidence():
    evidence = [
        make_evidence("Hiring Spike", "the company announced a hiring spike"),
        make_evidence("Layoffs", "the company also announced layoffs"),
    ]
    report = ContradictionDetector().detect(evidence)
    finding = report.findings[0]

    assert finding.evidence_a.evidence_id is not None
    assert finding.evidence_b.evidence_id is not None
    assert finding.evidence_a.evidence_id != finding.evidence_b.evidence_id


def test_multiple_themes_can_be_detected_simultaneously():
    evidence = [
        make_evidence("Hiring Spike", "hiring spike underway"),
        make_evidence("Layoffs", "layoffs also announced"),
        make_evidence("Series B", "series b funding round closed"),
        make_evidence("Budget Cuts", "budget cuts announced across departments"),
    ]
    report = ContradictionDetector().detect(evidence)

    themes = {f.theme for f in report.findings}
    assert "hiring_trajectory" in themes
    assert "financial_trajectory" in themes


def test_summary_mentions_contradiction_count():
    evidence = [
        make_evidence("Hiring Spike", "hiring spike underway"),
        make_evidence("Layoffs", "layoffs also announced"),
    ]
    report = ContradictionDetector().detect(evidence)
    assert "1" in report.summary
