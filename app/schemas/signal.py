"""Pydantic schemas for raw collector output, before evidence extraction."""
from pydantic import BaseModel, Field

from app.models.signal import SignalSource


class RawSignal(BaseModel):
    source: SignalSource
    category: str = Field(..., description="e.g. 'careers', 'funding', 'tech_stack', 'blog'")
    payload: dict = Field(default_factory=dict)
    url: str | None = None


class CollectorResult(BaseModel):
    company_domain: str
    source: SignalSource
    signals: list[RawSignal] = Field(default_factory=list)
    is_live: bool = Field(..., description="False when the collector ran in stub mode (no API key)")
    errors: list[str] = Field(default_factory=list)
