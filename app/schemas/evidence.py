"""Pydantic schemas for the Evidence Extraction Layer.

Per spec: the LLM must never invent facts. Every extracted insight is
required to carry a source, a verbatim-or-close excerpt, and a confidence
score in [0, 1]. `EvidenceExtractor` implementations should refuse to emit
an EvidenceItem that lacks any of these.

`category` and `collector` are populated by the `EvidenceNormalizer`
(app/services/evidence_normalizer.py) after extraction, not by the LLM -
they're inferred from which collector produced the underlying raw signal
and what kind of signal it is, so every evidence item is traceable back to
where it came from without the extractor needing to know about collector
internals. `pillar` is populated later still, when a scoring agent matches
the evidence against its keyword set - it starts unset because a single
extraction pass has no notion of "pillar" yet.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


class EvidenceItem(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    signal_label: str = Field(..., description="Short human-readable label, e.g. 'Hiring AI Engineers'")
    excerpt: str = Field(..., min_length=1, description="The text evidence was extracted from")
    source: str = Field(..., description="e.g. 'Careers Page', 'Google News', 'Wappalyzer'")
    url: HttpUrl | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    published_at: datetime | None = Field(
        default=None,
        description=(
            "When the underlying signal was published/observed, if determinable "
            "(e.g. a news article's publish date). Null when unknown - the Urgency "
            "scorer treats unknown recency as moderate-weight rather than assuming "
            "it's either fresh or stale."
        ),
    )
    category: str | None = Field(
        default=None,
        description=(
            "Evidence group, e.g. 'hiring', 'funding', 'technology', 'expansion'. "
            "Set by EvidenceNormalizer, not the extractor - see module docstring."
        ),
    )
    collector: str | None = Field(
        default=None,
        description="Which collector's signal this evidence traces back to (search/website/tech/news).",
    )
    pillar: str | None = Field(
        default=None,
        description="Which scoring pillar this evidence matched, set once a scoring agent claims it.",
    )

    # Structured Technology fields - set by EvidenceNormalizer (not the
    # extractor) by matching this item's `url` back to the Tech Collector's
    # RawSignal, same convention as `category`/`collector` above. Null for
    # non-technology evidence.
    technology_name: str | None = Field(
        default=None, description="e.g. 'React', 'AWS' - the exact technology BuiltWith/Wappalyzer detected."
    )
    technology_provider: str | None = Field(
        default=None, description="Which tech-detection provider found it: 'builtwith' or 'wappalyzer'."
    )

    # Structured company-profile fields - set by EvidenceNormalizer from the
    # Company Profile Collector's RawSignal.payload (homepage schema.org
    # JSON-LD and/or Wikidata - see app/collectors/company_profile_collector.py).
    # Two independently-sourced values for the same field are exactly what
    # ContradictionDetector's structured-fact checks compare (see that
    # module). Null for evidence that isn't a company-profile fact.
    employee_count: int | None = Field(
        default=None, description="Reported headcount, parsed from schema.org numberOfEmployees or Wikidata P1128."
    )
    founding_year: int | None = Field(
        default=None, description="Reported founding year, parsed from schema.org foundingDate or Wikidata P571."
    )

    # Structured Jobs fields - set the same way from the Jobs Collector's
    # RawSignal.payload (Greenhouse/Lever). Null for non-jobs evidence.
    job_title: str | None = Field(default=None, description="The job posting's title, e.g. 'Senior ML Engineer'.")
    job_department: str | None = Field(default=None, description="The posting's department/team, if the ATS reports one.")
    job_location: str | None = Field(default=None, description="The posting's location, if the ATS reports one.")
    job_ats_provider: str | None = Field(
        default=None, description="Which ATS the posting came from: 'greenhouse' or 'lever'."
    )
    job_posting_date: datetime | None = Field(
        default=None, description="When the posting went live, per the ATS - distinct from `published_at`."
    )

    @field_validator("excerpt")
    @classmethod
    def excerpt_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("excerpt must not be blank - evidence requires a grounding text span")
        return v


class EvidenceBatch(BaseModel):
    company_domain: str
    items: list[EvidenceItem] = Field(default_factory=list)


class EvidenceRecord(BaseModel):
    """Read schema for a persisted Evidence row - what the frontend's
    evidence cards render (source, url, date, confidence, collector,
    category, pillar, excerpt)."""

    id: uuid.UUID
    signal_label: str
    excerpt: str
    source: str
    url: str | None
    confidence: float
    category: str | None
    collector: str | None
    pillar: str | None
    published_at: datetime | None
    technology_name: str | None
    technology_provider: str | None
    employee_count: int | None
    founding_year: int | None
    job_title: str | None
    job_department: str | None
    job_location: str | None
    job_ats_provider: str | None
    job_posting_date: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
