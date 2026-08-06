"""Raw/normalized signal ORM model (output of the Signal Collection Layer)."""
import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SignalSource(StrEnum):
    SEARCH = "search"
    WEBSITE = "website"
    TECH = "tech"
    NEWS = "news"


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[SignalSource] = mapped_column(Enum(SignalSource), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="signals")

    def __repr__(self) -> str:
        return f"<Signal id={self.id} source={self.source} category={self.category!r}>"
