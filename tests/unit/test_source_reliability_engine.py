from app.decision.source_reliability import ReliabilityTier, SourceReliabilityEngine
from app.schemas.evidence import EvidenceItem


def make_evidence(collector):
    return EvidenceItem(signal_label="x", excerpt="y", source="z", confidence=0.8, collector=collector)


def test_github_and_tech_are_high_reliability():
    assert SourceReliabilityEngine.tier_for_collector("github") == ReliabilityTier.HIGH
    assert SourceReliabilityEngine.tier_for_collector("tech") == ReliabilityTier.HIGH
    assert SourceReliabilityEngine.weight_for_collector("github") == 1.0


def test_website_and_news_are_medium_reliability():
    assert SourceReliabilityEngine.tier_for_collector("website") == ReliabilityTier.MEDIUM
    assert SourceReliabilityEngine.tier_for_collector("news") == ReliabilityTier.MEDIUM
    assert SourceReliabilityEngine.weight_for_collector("news") == 0.65


def test_search_is_low_reliability():
    assert SourceReliabilityEngine.tier_for_collector("search") == ReliabilityTier.LOW
    assert SourceReliabilityEngine.weight_for_collector("search") == 0.4


def test_unrecognized_collector_defaults_to_low_not_high():
    assert SourceReliabilityEngine.tier_for_collector("mystery_source") == ReliabilityTier.LOW


def test_none_collector_defaults_to_low():
    assert SourceReliabilityEngine.tier_for_collector(None) == ReliabilityTier.LOW


def test_summarize_groups_by_collector_with_counts():
    evidence = [
        make_evidence("github"),
        make_evidence("github"),
        make_evidence("news"),
        make_evidence(None),
    ]
    summary = SourceReliabilityEngine().summarize(evidence)
    by_collector = {row.collector: row for row in summary}

    assert by_collector["github"].evidence_count == 2
    assert by_collector["github"].tier == "high"
    assert by_collector["news"].evidence_count == 1
    assert by_collector["unknown"].evidence_count == 1


def test_summarize_empty_evidence_returns_empty_list():
    assert SourceReliabilityEngine().summarize([]) == []


def test_every_row_has_a_nonempty_rationale():
    evidence = [make_evidence("github"), make_evidence("search")]
    summary = SourceReliabilityEngine().summarize(evidence)
    assert all(row.rationale.strip() for row in summary)
