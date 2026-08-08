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
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Float, String, Text, Uuid, func
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

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="evidence_items")

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} signal_label={self.signal_label!r} confidence={self.confidence}>"
