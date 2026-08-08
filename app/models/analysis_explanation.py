"""Analysis Explanation ORM model.

Stores the full AnalysisExplanation bundle as JSON, one row per analysis
run (mirroring how Recommendation is stored - "latest by created_at" wins
on read). A single JSON payload column rather than dozens of typed columns
is a deliberate trade-off: the Pydantic schema in app/schemas/explanation.py
is what stays strongly typed for the API and frontend; the DB just needs to
round-trip it faithfully, and collector-run details (which sources were
live, what errored) genuinely don't have a natural relational shape that's
worth a handful of extra tables for.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AnalysisExplanationRecord(Base):
    __tablename__ = "analysis_explanations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="explanations")

    def __repr__(self) -> str:
        return f"<AnalysisExplanationRecord id={self.id} company_id={self.company_id}>"
