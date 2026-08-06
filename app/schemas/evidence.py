"""Pydantic schemas for the Evidence Extraction Layer.

Per spec: the LLM must never invent facts. Every extracted insight is
required to carry a source, a verbatim-or-close excerpt, and a confidence
score in [0, 1]. `EvidenceExtractor` implementations should refuse to emit
an EvidenceItem that lacks any of these.
"""
from pydantic import BaseModel, Field, HttpUrl, field_validator


class EvidenceItem(BaseModel):
    signal_label: str = Field(..., description="Short human-readable label, e.g. 'Hiring AI Engineers'")
    excerpt: str = Field(..., min_length=1, description="The text evidence was extracted from")
    source: str = Field(..., description="e.g. 'Careers Page', 'Google News', 'Wappalyzer'")
    url: HttpUrl | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("excerpt")
    @classmethod
    def excerpt_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("excerpt must not be blank - evidence requires a grounding text span")
        return v


class EvidenceBatch(BaseModel):
    company_domain: str
    items: list[EvidenceItem] = Field(default_factory=list)
