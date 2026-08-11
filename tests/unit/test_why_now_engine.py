from datetime import UTC, datetime, timedelta

from app.decision.why_now_engine import WhyNowEngine
from app.schemas.evidence import EvidenceItem


def make_evidence(label, excerpt, published_at=None):
    return EvidenceItem(
        signal_label=label, excerpt=excerpt, source="News", confidence=0.8, published_at=published_at
    )


def test_no_evidence_means_data_insufficient_not_no_trigger():
    explanation = WhyNowEngine().explain([])
    assert explanation.has_timing_trigger is False
    assert explanation.data_sufficient is False
    assert "no evidence" in explanation.narrative.lower()


def test_evidence_present_but_no_trigger_phrases_is_a_genuine_no():
    evidence = [make_evidence("Office Photo", "a photo of the lobby", published_at=datetime.now(UTC))]
    explanation = WhyNowEngine().explain(evidence)

    assert explanation.has_timing_trigger is False
    assert explanation.data_sufficient is True


def test_fresh_funding_event_is_a_timing_trigger():
    now = datetime.now(UTC)
    evidence = [make_evidence("Funding News", "the company closed a series b funding round", published_at=now - timedelta(days=5))]
    explanation = WhyNowEngine().explain(evidence)

    assert explanation.has_timing_trigger is True
    assert explanation.triggers[0].trigger_type == "funding_event"


def test_stale_trigger_phrase_does_not_count_as_why_now():
    """A funding round mentioned in evidence from over a year ago shouldn't
    read as a reason to reach out *today*."""
    now = datetime.now(UTC)
    evidence = [make_evidence("Old Funding", "the company raised a series a round", published_at=now - timedelta(days=800))]
    explanation = WhyNowEngine().explain(evidence)

    assert explanation.has_timing_trigger is False
    assert explanation.data_sufficient is True


def test_undated_trigger_phrase_does_not_count_as_why_now():
    """Unknown recency gets weight 0.5, below the 0.7 trigger threshold -
    we should not claim timing urgency for evidence we can't date."""
    evidence = [make_evidence("Undated Funding", "the company raised a series b round", published_at=None)]
    explanation = WhyNowEngine().explain(evidence)

    assert explanation.has_timing_trigger is False


def test_triggers_sorted_most_recent_first():
    now = datetime.now(UTC)
    older = make_evidence("Expansion", "opens a new office", published_at=now - timedelta(days=60))
    newer = make_evidence("Funding", "closed a series a round", published_at=now - timedelta(days=2))
    explanation = WhyNowEngine().explain([older, newer])

    assert explanation.triggers[0].evidence_id == newer.id


def test_triggers_capped_at_five():
    now = datetime.now(UTC)
    evidence = [
        make_evidence(f"Funding {i}", "closed a series a round", published_at=now - timedelta(days=i))
        for i in range(10)
    ]
    explanation = WhyNowEngine().explain(evidence)
    assert len(explanation.triggers) == 5


def test_narrative_cites_the_leading_trigger():
    now = datetime.now(UTC)
    evidence = [make_evidence("New CEO", "the company appoints a new ceo", published_at=now - timedelta(days=1))]
    explanation = WhyNowEngine().explain(evidence)

    assert "leadership" in explanation.narrative.lower()
