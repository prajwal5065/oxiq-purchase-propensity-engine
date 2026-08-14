from app.models.signal import SignalSource
from app.schemas.evidence import EvidenceItem
from app.schemas.signal import RawSignal
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


def test_normalizer_infers_collector_for_greenhouse_source():
    items = [make_item("Hiring ML Engineer", "posting for a machine learning engineer", source="Greenhouse")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].collector == "jobs"


def test_normalizer_infers_collector_for_lever_source():
    items = [make_item("Hiring", "open posting", source="Lever Job Board")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].collector == "jobs"


def test_normalizer_infers_website_collector_for_generic_career_source_unchanged():
    """Guards against the new jobs-source keywords swallowing the existing
    generic 'career'/'job' -> website mapping."""
    items = [make_item("Hiring", "we are hiring engineers", source="Careers Page")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].collector == "website"


def test_normalizer_inherits_jobs_hiring_subtype_category_via_url_match():
    raw_signals = [
        RawSignal(
            source=SignalSource.JOBS,
            category="ai_ml_hiring",
            payload={"title": "Machine Learning Engineer"},
            url="https://boards.greenhouse.io/acme/jobs/1",
        )
    ]
    items = [
        make_item(
            "Hiring ML Engineer",
            "Acme is hiring a Machine Learning Engineer",
            source="Greenhouse",
        ).model_copy(update={"url": "https://boards.greenhouse.io/acme/jobs/1"})
    ]
    normalized = EvidenceNormalizer().normalize(raw_signals=raw_signals, items=items)
    assert normalized[0].category == "ai_ml_hiring"


def test_normalizer_does_not_inherit_category_for_non_jobs_raw_signal_categories():
    """Only the six jobs hiring-subtype category values are ever inherited
    via URL match - an arbitrary RawSignal.category from another collector
    must never leak into EvidenceItem.category this way."""
    raw_signals = [
        RawSignal(
            source=SignalSource.GITHUB,
            category="ai_projects",
            payload={},
            url="https://github.com/acme/ml-repo",
        )
    ]
    items = [
        make_item("Open source AI project", "flagship ml repo", source="GitHub").model_copy(
            update={"url": "https://github.com/acme/ml-repo"}
        )
    ]
    normalized = EvidenceNormalizer().normalize(raw_signals=raw_signals, items=items)
    # Falls back to the ordinary keyword heuristic, not the RawSignal's own category.
    assert normalized[0].category != "ai_projects"


def test_normalizer_falls_back_to_keyword_inference_when_no_url_match():
    items = [make_item("Hiring AI Engineers", "we are hiring an AI engineer", source="Careers Page")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].category == "hiring"


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


# --- Structured Technology/Jobs field enrichment ---------------------------


def test_normalizer_attaches_technology_fields_via_url_match():
    raw_signals = [
        RawSignal(
            source=SignalSource.TECH,
            category="javascript",
            payload={"technology": "React", "provider": "builtwith"},
            url="https://acme.com/#tech-React",
        )
    ]
    items = [
        make_item("Uses React", "The site is built with React", source="BuiltWith").model_copy(
            update={"url": "https://acme.com/#tech-React"}
        )
    ]
    normalized = EvidenceNormalizer().normalize(raw_signals=raw_signals, items=items)
    assert normalized[0].technology_name == "React"
    assert normalized[0].technology_provider == "builtwith"


def test_normalizer_attaches_wappalyzer_technology_fields():
    raw_signals = [
        RawSignal(
            source=SignalSource.TECH,
            category="Analytics",
            payload={"technology": "Google Analytics", "provider": "wappalyzer"},
            url="https://acme.com/#tech-Google%20Analytics",
        )
    ]
    items = [
        make_item("Uses Google Analytics", "Tracking via Google Analytics", source="Wappalyzer").model_copy(
            update={"url": "https://acme.com/#tech-Google%20Analytics"}
        )
    ]
    normalized = EvidenceNormalizer().normalize(raw_signals=raw_signals, items=items)
    assert normalized[0].technology_name == "Google Analytics"
    assert normalized[0].technology_provider == "wappalyzer"


def test_normalizer_leaves_technology_fields_null_when_no_url_match():
    items = [make_item("Uses React", "The site is built with React", source="BuiltWith")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].technology_name is None
    assert normalized[0].technology_provider is None


def test_normalizer_does_not_attach_technology_fields_from_unrelated_source():
    """A GitHub RawSignal must never leak technology_name/provider onto
    unrelated evidence, even if URLs happened to collide."""
    raw_signals = [
        RawSignal(
            source=SignalSource.GITHUB,
            category="repo",
            payload={"stars": 100},
            url="https://acme.com/#tech-React",
        )
    ]
    items = [
        make_item("Uses React", "built with React", source="BuiltWith").model_copy(
            update={"url": "https://acme.com/#tech-React"}
        )
    ]
    normalized = EvidenceNormalizer().normalize(raw_signals=raw_signals, items=items)
    assert normalized[0].technology_name is None
    assert normalized[0].technology_provider is None


def test_normalizer_attaches_job_fields_via_url_match():
    raw_signals = [
        RawSignal(
            source=SignalSource.JOBS,
            category="ai_ml_hiring",
            payload={
                "title": "Machine Learning Engineer",
                "department": "Engineering",
                "location": "Remote",
                "posted_at": "2026-08-01T00:00:00+00:00",
                "provider": "greenhouse",
                "description_snippet": "Join our ML team...",
            },
            url="https://boards.greenhouse.io/acme/jobs/1",
        )
    ]
    items = [
        make_item(
            "Hiring ML Engineer", "Acme is hiring a Machine Learning Engineer", source="Greenhouse"
        ).model_copy(update={"url": "https://boards.greenhouse.io/acme/jobs/1"})
    ]
    normalized = EvidenceNormalizer().normalize(raw_signals=raw_signals, items=items)
    assert normalized[0].job_title == "Machine Learning Engineer"
    assert normalized[0].job_department == "Engineering"
    assert normalized[0].job_location == "Remote"
    assert normalized[0].job_ats_provider == "greenhouse"
    assert normalized[0].job_posting_date is not None
    assert normalized[0].job_posting_date.year == 2026


def test_normalizer_attaches_lever_job_fields():
    raw_signals = [
        RawSignal(
            source=SignalSource.JOBS,
            category="engineering_hiring",
            payload={
                "title": "Staff Engineer",
                "department": "Platform",
                "location": "New York",
                "posted_at": None,
                "provider": "lever",
                "description_snippet": "...",
            },
            url="https://jobs.lever.co/acme/2",
        )
    ]
    items = [
        make_item("Hiring Staff Engineer", "Acme is hiring a Staff Engineer", source="Lever Job Board").model_copy(
            update={"url": "https://jobs.lever.co/acme/2"}
        )
    ]
    normalized = EvidenceNormalizer().normalize(raw_signals=raw_signals, items=items)
    assert normalized[0].job_title == "Staff Engineer"
    assert normalized[0].job_department == "Platform"
    assert normalized[0].job_location == "New York"
    assert normalized[0].job_ats_provider == "lever"
    assert normalized[0].job_posting_date is None


def test_normalizer_leaves_job_fields_null_when_no_url_match():
    items = [make_item("Hiring", "open posting", source="Greenhouse")]
    normalized = EvidenceNormalizer().normalize(raw_signals=[], items=items)
    assert normalized[0].job_title is None
    assert normalized[0].job_department is None
    assert normalized[0].job_location is None
    assert normalized[0].job_ats_provider is None
    assert normalized[0].job_posting_date is None


def test_normalizer_does_not_cross_contaminate_tech_and_job_fields():
    """A tech item must never pick up job_* fields and vice versa, even
    when both a tech and a jobs raw signal are present in the same batch."""
    raw_signals = [
        RawSignal(
            source=SignalSource.TECH,
            category="javascript",
            payload={"technology": "React", "provider": "builtwith"},
            url="https://acme.com/#tech-React",
        ),
        RawSignal(
            source=SignalSource.JOBS,
            category="engineering_hiring",
            payload={
                "title": "Backend Engineer",
                "department": "Eng",
                "location": "Remote",
                "posted_at": None,
                "provider": "greenhouse",
                "description_snippet": "...",
            },
            url="https://boards.greenhouse.io/acme/jobs/2",
        ),
    ]
    items = [
        make_item("Uses React", "built with React", source="BuiltWith").model_copy(
            update={"url": "https://acme.com/#tech-React"}
        ),
        make_item("Hiring Backend Engineer", "Acme is hiring", source="Greenhouse").model_copy(
            update={"url": "https://boards.greenhouse.io/acme/jobs/2"}
        ),
    ]
    normalized = EvidenceNormalizer().normalize(raw_signals=raw_signals, items=items)
    tech_item = next(i for i in normalized if i.technology_name is not None)
    job_item = next(i for i in normalized if i.job_title is not None)

    assert tech_item.job_title is None
    assert job_item.technology_name is None
