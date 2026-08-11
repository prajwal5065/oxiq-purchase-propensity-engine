from app.schemas.evidence import EvidenceItem
from app.services.evidence_normalizer import EvidenceNormalizer


def make_item(label: str, excerpt: str, source: str, confidence: float = 0.8) -> EvidenceItem:
    return EvidenceItem(signal_label=label, excerpt=excerpt, source=source, confidence=confidence)


def test_normalizer_infers_collector_from_source_string():
    items = [make_item("Hiring", "we are hiring engineers", source="Careers Page")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].collector == "website"


def test_normalizer_infers_collector_for_news_source():
    items = [make_item("Funding round", "raised a Series B", source="Google News")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].collector == "news"


def test_normalizer_falls_back_to_unknown_collector():
    items = [make_item("Something", "unclear excerpt", source="Mystery Source")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].collector == "unknown"


def test_normalizer_infers_collector_for_github_source():
    items = [make_item("Open source AI project", "flagship ml repo", source="GitHub")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].collector == "github"


def test_normalizer_infers_collector_for_wikidata_source():
    items = [make_item("Industry", "operates in the software industry", source="Wikidata")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].collector == "company_profile"


def test_normalizer_infers_collector_for_company_profile_source():
    items = [make_item("Employee count", "reports 500 employees", source="Company Profile")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].collector == "company_profile"


def test_normalizer_infers_category_from_keywords():
    items = [make_item("Hiring AI Engineers", "we are hiring an AI engineer", source="Careers Page")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].category == "hiring"


def test_normalizer_infers_company_profile_category():
    items = [make_item("Industry", "the company is headquartered in Austin", source="Wikidata")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].category == "company_profile"


def test_normalizer_falls_back_to_general_category():
    items = [make_item("Vague", "this text matches no category keyword", source="Website")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].category == "general"


def test_normalizer_dedupes_identical_source_and_excerpt():
    items = [
        make_item("Hiring", "we are hiring", source="Careers Page"),
        make_item("Hiring (dup)", "we are hiring", source="Careers Page"),
    ]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert len(normalized) == 1


def test_normalizer_keeps_existing_category_and_collector_if_already_set():
    item = EvidenceItem(
        signal_label="Custom",
        excerpt="already tagged",
        source="Careers Page",
        confidence=0.9,
        category="funding",
        collector="search",
    )
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=[item])
    assert normalized[0].category == "funding"
    assert normalized[0].collector == "search"
