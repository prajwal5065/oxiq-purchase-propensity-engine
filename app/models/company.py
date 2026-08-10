"""Company ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    signals: Mapped[list["Signal"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    evidence_items: Mapped[list["Evidence"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    scores: Mapped[list["Score"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    explanations: Mapped[list["AnalysisExplanationRecord"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} domain={self.domain!r}>"
