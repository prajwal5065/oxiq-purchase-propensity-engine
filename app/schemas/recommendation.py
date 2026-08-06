"""Pydantic schema for the Recommendation Generator's output."""
from pydantic import BaseModel, Field


class RecommendationResult(BaseModel):
    executive_summary: str
    fit_reasons: list[str] = Field(default_factory=list)
    top_buying_signals: list[str] = Field(default_factory=list)
    top_risks: list[str] = Field(default_factory=list)
    suggested_approach: str
    contact_priority: str = Field(..., description="'high' | 'medium' | 'low'")
    solution_match: str | None = Field(
        default=None,
        description=(
            "Best-fit OxiQ offering for this company. Not implemented: this requires a "
            "product/offering catalog that hasn't been provided yet."
        ),
    )
