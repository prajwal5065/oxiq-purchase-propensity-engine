"""Score ORM model. Stores both pillar scores and the final aggregate."""
import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ScoreType(StrEnum):
    NEED = "need"
    URGENCY = "urgency"
    CAPACITY = "capacity"
    DIGITAL_MATURITY = "digital_maturity"
    ORG_READINESS = "org_readiness"
    WINNABILITY = "winnability"
    PURCHASE_PROPENSITY = "purchase_propensity"


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score_type: Mapped[ScoreType] = mapped_column(Enum(ScoreType), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="scores")

    def __repr__(self) -> str:
        return f"<Score id={self.id} type={self.score_type} value={self.value}>"
