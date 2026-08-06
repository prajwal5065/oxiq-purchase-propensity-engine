"""Pydantic schemas for the Evidence Extraction Layer.

Per spec: the LLM must never invent facts. Every extracted insight is
required to carry a source, a verbatim-or-close excerpt, and a confidence
score in [0, 1]. `EvidenceExtractor` implementations should refuse to emit
an EvidenceItem that lacks any of these.
"""
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


class EvidenceItem(BaseModel):
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

    @field_validator("excerpt")
    @classmethod
    def excerpt_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("excerpt must not be blank - evidence requires a grounding text span")
        return v


class EvidenceBatch(BaseModel):
    company_domain: str
    items: list[EvidenceItem] = Field(default_factory=list)
