"""Pydantic schemas for raw collector output, before evidence extraction."""
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.signal import SignalSource


class RawSignal(BaseModel):
    source: SignalSource
    category: str = Field(..., description="e.g. 'careers', 'funding', 'tech_stack', 'blog'")
    payload: dict = Field(default_factory=dict)
    url: str | None = None


class CollectorStatus(StrEnum):
    """What actually happened when a collector ran - the distinction the
    evidence-first architecture insists on (spec Stage 1/6/7): a collector
    that succeeded with zero results is not the same thing as one that
    never ran, and neither is the same thing as one that errored out."""

    SUCCESS = "success"
    NO_RESULTS = "no_results"
    NOT_CONFIGURED = "not_configured"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"
    ERROR = "error"


class CollectorResult(BaseModel):
    company_domain: str
    source: SignalSource
    signals: list[RawSignal] = Field(default_factory=list)
    is_live: bool = Field(..., description="False when the collector ran in stub mode (no API key)")
    errors: list[str] = Field(default_factory=list)
    status: CollectorStatus | None = Field(
        default=None,
        description=(
            "Explicit status when the collector knows more than is_live/signals/errors "
            "alone can convey (e.g. NOT_CONFIGURED in a stub-mode branch, or BLOCKED when "
            "a live call gets a 403/429). When unset, use `resolved_status` below, which "
            "infers the same taxonomy from is_live/signals/errors."
        ),
    )

    @property
    def resolved_status(self) -> CollectorStatus:
        if self.status is not None:
            return self.status
        if not self.is_live:
            return CollectorStatus.NOT_CONFIGURED
        if self.signals:
            return CollectorStatus.SUCCESS
        if not self.errors:
            return CollectorStatus.NO_RESULTS
        error_text = " ".join(self.errors).lower()
        if "timeout" in error_text:
            return CollectorStatus.TIMEOUT
        if any(marker in error_text for marker in ("403", "429", "forbidden", "blocked", "captcha")):
            return CollectorStatus.BLOCKED
        return CollectorStatus.ERROR
