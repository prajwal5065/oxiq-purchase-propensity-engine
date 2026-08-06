"""Recommendation ORM model (output of the Recommendation Generator)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    fit_reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    top_buying_signals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    top_risks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    suggested_approach: Mapped[str] = mapped_column(Text, nullable=False)
    contact_priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} company_id={self.company_id}>"
