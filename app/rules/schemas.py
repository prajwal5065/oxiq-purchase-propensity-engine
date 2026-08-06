"""Schemas for the Rule Engine's configuration file.

Rules are data, not code: a structured (field, operator, threshold) shape
that gets evaluated safely, rather than an eval()'d expression string. That
keeps the Rule Engine genuinely configurable (spec requirement) without
letting a config file execute arbitrary Python.
"""
from enum import StrEnum

from pydantic import BaseModel, Field


class RuleOperator(StrEnum):
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    EQ = "eq"


class RuleCondition(BaseModel):
    field: str = Field(..., description="Pillar score name, e.g. 'capacity', or 'overall_confidence'")
    operator: RuleOperator
    value: float


class DisqualifierRule(BaseModel):
    id: str
    description: str
    condition: RuleCondition


class AdjustmentAction(StrEnum):
    MULTIPLY = "multiply"
    CAP = "cap"
    FLOOR = "floor"


class AdjustmentRule(BaseModel):
    id: str
    description: str
    condition: RuleCondition
    action: AdjustmentAction
    action_value: float


class IndustryPrior(BaseModel):
    industry: str
    multiplier: float = Field(..., description="Applied to the aggregate purchase score")


class RuleEngineConfig(BaseModel):
    disqualifiers: list[DisqualifierRule] = Field(default_factory=list)
    adjustments: list[AdjustmentRule] = Field(default_factory=list)
    industry_priors: list[IndustryPrior] = Field(default_factory=list)
    default_industry_prior: float = 1.0
