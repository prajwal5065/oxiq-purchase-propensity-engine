from app.decision.buying_intent_engine import BuyingIntentEngine
from app.schemas.decision import BuyingIntentLevel
from app.schemas.evidence import EvidenceItem


def make_evidence(label, excerpt="", confidence=0.8):
    return EvidenceItem(signal_label=label, excerpt=excerpt or label, source="News", confidence=confidence)


def test_strong_signal_detected_when_rfp_language_present():
    evidence = [make_evidence("Vendor Evaluation", "the company issued an RFP for automation tools")]
    result = BuyingIntentEngine().assess(evidence, coverage_percentage=0.8, evidence_items_accepted=5)

    assert result.level == BuyingIntentLevel.STRONG
    assert result.score == 1.0
    assert len(result.matched_signals) == 1
    assert result.matched_signals[0].strength == "strong"


def test_moderate_signal_detected_when_no_strong_signal_present():
    evidence = [make_evidence("Team Growth", "they are expanding team headcount this quarter")]
    result = BuyingIntentEngine().assess(evidence, coverage_percentage=0.8, evidence_items_accepted=5)

    assert result.level == BuyingIntentLevel.MODERATE


def test_weak_signal_detected_when_only_exploratory_language_present():
    evidence = [make_evidence("Early Interest", "leadership is exploring AI options")]
    result = BuyingIntentEngine().assess(evidence, coverage_percentage=0.8, evidence_items_accepted=5)

    assert result.level == BuyingIntentLevel.WEAK


def test_strong_signal_wins_over_moderate_and_weak_when_multiple_present():
    evidence = [
        make_evidence("Early Interest", "exploring AI options"),
        make_evidence("Team Growth", "expanding team"),
        make_evidence("RFP Issued", "budget approved for a pilot program"),
    ]
    result = BuyingIntentEngine().assess(evidence, coverage_percentage=0.8, evidence_items_accepted=5)

    assert result.level == BuyingIntentLevel.STRONG


def test_none_level_when_coverage_sufficient_but_no_signals_found():
    evidence = [make_evidence("Office Photo", "a photo of the new office lobby")]
    result = BuyingIntentEngine().assess(evidence, coverage_percentage=0.9, evidence_items_accepted=10)

    assert result.level == BuyingIntentLevel.NONE
    assert result.score == 0.0


def test_insufficient_data_guardrail_when_coverage_too_thin_and_no_signals():
    evidence = [make_evidence("Office Photo", "a photo of the new office lobby")]
    result = BuyingIntentEngine().assess(evidence, coverage_percentage=0.1, evidence_items_accepted=1)

    assert result.level == BuyingIntentLevel.INSUFFICIENT_DATA
    assert "coverage" in result.rationale.lower()


def test_insufficient_data_guardrail_with_zero_evidence():
    result = BuyingIntentEngine().assess([], coverage_percentage=0.0, evidence_items_accepted=0)
    assert result.level == BuyingIntentLevel.INSUFFICIENT_DATA


def test_strong_signal_overrides_insufficient_coverage_guardrail():
    """Even with thin overall coverage, if we DID find explicit buying-intent
    language, that's a genuine finding - the guardrail only protects against
    reporting an absence of signal as a conclusion, not a presence of one."""
    evidence = [make_evidence("RFP Issued", "the company issued a request for proposal")]
    result = BuyingIntentEngine().assess(evidence, coverage_percentage=0.1, evidence_items_accepted=1)

    assert result.level == BuyingIntentLevel.STRONG


def test_matched_signals_are_capped_and_traceable():
    evidence = [make_evidence(f"RFP {i}", "request for proposal issued") for i in range(20)]
    result = BuyingIntentEngine().assess(evidence, coverage_percentage=0.9, evidence_items_accepted=20)

    assert len(result.matched_signals) == 8
    assert all(sig.evidence_id is not None for sig in result.matched_signals)
