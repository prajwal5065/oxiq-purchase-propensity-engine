"""Recommendation ORM model (output of the Recommendation Generator)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    fit_reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    top_buying_signals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    top_risks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    suggested_approach: Mapped[str] = mapped_column(Text, nullable=False)
    contact_priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    solution_match: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Best-fit OxiQ offering; null until a product catalog is wired in"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} company_id={self.company_id}>"
