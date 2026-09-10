from app.extraction.evidence_extractor import EvidenceExtractor
from app.models.signal import SignalSource
from app.schemas.signal import RawSignal


def _signal(url: str | None, source: SignalSource = SignalSource.SEARCH) -> RawSignal:
    return RawSignal(source=source, category="news", payload={"title": "x", "content": "y"}, url=url)


def test_binds_url_from_raw_signal_by_index():
    raw_signals = [_signal("https://techcrunch.com/2026/08/acme-raises-10m")]
    raw = {"signal_label": "Funding", "excerpt": "raised $10M", "source": "search", "signal_index": 0, "confidence": 0.8}

    bound = EvidenceExtractor._bind_source_and_url(raw, raw_signals)

    assert bound["url"] == "https://techcrunch.com/2026/08/acme-raises-10m"


def test_replaces_generic_source_label_with_domain():
    raw_signals = [_signal("https://techcrunch.com/2026/08/acme-raises-10m")]
    raw = {"signal_label": "Funding", "excerpt": "raised $10M", "source": "search", "signal_index": 0, "confidence": 0.8}

    bound = EvidenceExtractor._bind_source_and_url(raw, raw_signals)

    assert bound["source"] == "techcrunch.com"


def test_keeps_specific_llm_provided_source_name():
    raw_signals = [_signal("https://techcrunch.com/2026/08/acme-raises-10m")]
    raw = {
        "signal_label": "Funding",
        "excerpt": "raised $10M",
        "source": "TechCrunch",
        "signal_index": 0,
        "confidence": 0.8,
    }

    bound = EvidenceExtractor._bind_source_and_url(raw, raw_signals)

    # A specific, non-generic name the model already produced is left
    # alone - only the generic "search"/"news"-style fallback gets
    # replaced with the domain.
    assert bound["source"] == "TechCrunch"


def test_leaves_source_and_url_untouched_when_signal_index_missing():
    raw_signals = [_signal("https://techcrunch.com/x")]
    raw = {"signal_label": "Funding", "excerpt": "raised $10M", "source": "search", "confidence": 0.8}

    bound = EvidenceExtractor._bind_source_and_url(raw, raw_signals)

    assert bound == raw


def test_leaves_source_and_url_untouched_when_signal_index_out_of_range():
    raw_signals = [_signal("https://techcrunch.com/x")]
    raw = {
        "signal_label": "Funding",
        "excerpt": "raised $10M",
        "source": "search",
        "signal_index": 7,
        "confidence": 0.8,
    }

    bound = EvidenceExtractor._bind_source_and_url(raw, raw_signals)

    assert bound == {k: v for k, v in raw.items() if k != "signal_index"}


def test_does_not_override_source_when_raw_signal_has_no_url():
    raw_signals = [_signal(None)]
    raw = {"signal_label": "Funding", "excerpt": "raised $10M", "source": "search", "signal_index": 0, "confidence": 0.8}

    bound = EvidenceExtractor._bind_source_and_url(raw, raw_signals)

    assert bound["source"] == "search"
    assert "url" not in bound or bound.get("url") is None


def test_domain_from_url_strips_www():
    assert EvidenceExtractor._domain_from_url("https://www.forbes.com/some/article") == "forbes.com"


def test_parse_response_applies_signal_index_binding():
    raw_signals = [_signal("https://prnewswire.com/acme-announcement")]
    text = (
        '[{"signal_label": "Announcement", "excerpt": "Acme announces expansion", '
        '"source": "news", "signal_index": 0, "confidence": 0.9, "published_at": null}]'
    )

    items = EvidenceExtractor._parse_response(text, raw_signals)

    assert len(items) == 1
    assert str(items[0].url) == "https://prnewswire.com/acme-announcement"
    assert items[0].source == "prnewswire.com"
