"""Extracted evidence ORM model (output of the Evidence Extraction Layer).

Every row must be traceable to a source and carry a model confidence. The
extraction layer must never write an Evidence row without both.

`category`, `collector`, `pillar`, and `published_at` are the columns that
turn this from a flat "here's a quote" table into the Evidence Store the
architecture calls for: `category` groups evidence for the SignalAggregator
(hiring / funding / technology / ...), `collector` traces it back to which
Signal Collector produced the underlying raw signal, `pillar` records which
scoring agent claimed it once scoring runs, and `published_at` is the
signal's real-world date (as opposed to `created_at`, which is just when we
happened to store the row).

`technology_name`/`technology_provider` and `job_title`/`job_department`/
`job_location`/`job_ats_provider`/`job_posting_date` are structured fields
lifted straight from the Tech/Jobs Collectors' RawSignal.payload by
EvidenceNormalizer (matched to the extracted EvidenceItem by URL - see
that module's docstring). They exist because the LLM-extracted
`excerpt`/`signal_label` text alone doesn't let the frontend render a
proper Technology/Jobs table; these columns are additive next to the
existing text fields, never a replacement for them.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Float, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.score import ScoreType


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("signals.id", ondelete="SET NULL"), nullable=True
    )

    signal_label: Mapped[str] = mapped_column(String(255), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    collector: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    pillar: Mapped[ScoreType | None] = mapped_column(String(50), nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Structured Technology fields - populated by EvidenceNormalizer from the
    # RawSignal.payload the Tech Collector attached (BuiltWith primary,
    # Wappalyzer fallback - see app/collectors/tech_collector.py), matched
    # back to the EvidenceItem by URL. Null for non-technology evidence, or
    # when the extractor's item couldn't be matched to a raw tech signal.
    technology_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    technology_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Structured company-profile fields - populated by EvidenceNormalizer
    # from the Company Profile Collector's RawSignal.payload (homepage
    # schema.org JSON-LD and/or Wikidata). Null for non-company-profile
    # evidence. See ContradictionDetector for why two sources reporting
    # different values here matters.
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    founding_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Structured Jobs fields - populated the same way from the Jobs
    # Collector's RawSignal.payload (Greenhouse/Lever - see
    # app/collectors/jobs_collector.py). Null for non-jobs evidence.
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_ats_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    job_posting_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="evidence_items")

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} signal_label={self.signal_label!r} confidence={self.confidence}>"
