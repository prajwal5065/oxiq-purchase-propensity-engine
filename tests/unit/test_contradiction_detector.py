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


def _profile_evidence(source, employee_count=None, founding_year=None, location_kind=None, location_name=None):
    item = EvidenceItem(signal_label="Company profile", excerpt="company facts", source=source, confidence=0.9)
    return item.model_copy(
        update={
            "employee_count": employee_count,
            "founding_year": founding_year,
            "location_kind": location_kind,
            "location_name": location_name,
        }
    )


def test_detects_employee_count_conflict_beyond_tolerance():
    evidence = [
        _profile_evidence("Homepage", employee_count=500),
        _profile_evidence("Wikidata", employee_count=5000),
    ]
    report = ContradictionDetector().detect(evidence)
    assert any(f.theme == "employee_count_conflict" for f in report.findings)


def test_does_not_flag_employee_count_within_tolerance():
    evidence = [
        _profile_evidence("Homepage", employee_count=500),
        _profile_evidence("Wikidata", employee_count=520),
    ]
    report = ContradictionDetector().detect(evidence)
    assert not any(f.theme == "employee_count_conflict" for f in report.findings)


def test_does_not_flag_employee_count_with_only_one_source():
    evidence = [_profile_evidence("Homepage", employee_count=500)]
    report = ContradictionDetector().detect(evidence)
    assert report.has_contradictions is False


def test_detects_founding_year_conflict():
    evidence = [
        _profile_evidence("Homepage", founding_year=2015),
        _profile_evidence("Wikidata", founding_year=2009),
    ]
    report = ContradictionDetector().detect(evidence)
    assert any(f.theme == "founding_year_conflict" for f in report.findings)


def test_founding_year_and_employee_count_never_compared_against_each_other():
    """A field is only ever compared against itself - an employee_count
    value is never treated as if it disagreed with a founding_year value
    just because both are numbers on the same evidence item."""
    evidence = [_profile_evidence("Homepage", employee_count=2015, founding_year=None)]
    report = ContradictionDetector().detect(evidence)
    assert report.has_contradictions is False


def test_detects_headquarters_conflict():
    evidence = [
        _profile_evidence("Homepage", location_kind="headquarters", location_name="Mumbai, India"),
        _profile_evidence("Wikidata", location_kind="headquarters", location_name="Pune, India"),
    ]
    report = ContradictionDetector().detect(evidence)
    assert any(f.theme == "headquarters_conflict" for f in report.findings)


def test_does_not_flag_headquarters_when_names_are_the_same_place_at_different_granularity():
    evidence = [
        _profile_evidence("Homepage", location_kind="headquarters", location_name="Pune"),
        _profile_evidence("Wikidata", location_kind="headquarters", location_name="Pune, Maharashtra, India"),
    ]
    report = ContradictionDetector().detect(evidence)
    assert not any(f.theme == "headquarters_conflict" for f in report.findings)


def test_office_location_never_compared_as_headquarters():
    """A job posting's location_kind='office' must never be treated as a
    headquarters claim, even when it conflicts with a real HQ signal - an
    office/facility presence is not proof of (or against) headquarters."""
    evidence = [
        _profile_evidence("Homepage", location_kind="headquarters", location_name="Mumbai, India"),
        _profile_evidence("Job Posting", location_kind="office", location_name="Pune, India"),
    ]
    report = ContradictionDetector().detect(evidence)
    assert not any(f.theme == "headquarters_conflict" for f in report.findings)
