"""Registry of all scoring agents, used by the orchestrator (phase 6+) to
run every pillar scorer over a company's evidence in parallel.
"""
from app.scoring.base import BaseScoringAgent
from app.scoring.capacity_scorer import CapacityScoringAgent
from app.scoring.digital_maturity_scorer import DigitalMaturityScoringAgent
from app.scoring.need_scorer import NeedScoringAgent
from app.scoring.org_readiness_scorer import OrgReadinessScoringAgent
from app.scoring.urgency_scorer import UrgencyScoringAgent
from app.scoring.winnability_scorer import WinnabilityScoringAgent

ALL_SCORING_AGENTS: list[type[BaseScoringAgent]] = [
    NeedScoringAgent,
    UrgencyScoringAgent,
    CapacityScoringAgent,
    DigitalMaturityScoringAgent,
    OrgReadinessScoringAgent,
    WinnabilityScoringAgent,
]

__all__ = ["ALL_SCORING_AGENTS", "BaseScoringAgent"]
