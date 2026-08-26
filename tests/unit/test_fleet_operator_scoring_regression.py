"""Regression test for a real production bug report: strong evidence for a
non-software-vendor company (a bus/fleet operator with active EV
deployment) was not translating into Need, Digital Maturity, Org
Readiness, or Winnability scores at all.

Root cause was NOT an extraction bug - the evidence was already being
extracted correctly. It was twofold:

1. Every scoring agent's keyword vocabulary was written for evaluating an
   AI/software buyer (e.g. Need only recognized "hiring AI engineer", not
   any other kind of active operational need) and had no vocabulary for
   evidence phrased in other verticals' terms - so genuinely strong
   evidence (EV bus orders, fleet size, mass hiring, technology
   modernization) matched nothing and contributed nothing to any pillar.

2. The Rule Engine's "low score" penalty adjustments keyed purely off the
   numeric pillar score, never confidence - so a pillar that matched
   nothing (score=0, confidence=0, i.e. "we don't know") was penalized
   identically to one that was confidently, evidentially low. This
   directly violated "missing evidence != negative evidence".

These tests exercise the real scoring agents and rule engine end-to-end
against evidence shaped like the reported case, not mocks, so a
regression here is caught the same way it would show up in a real report.
"""
import pytest

from app.aggregation.purchase_aggregator import PurchaseAggregator
from app.decision.why_now_engine import WhyNowEngine
from app.schemas.evidence import EvidenceItem
from app.scoring.digital_maturity_scorer import DigitalMaturityScoringAgent
from app.scoring.need_scorer import NeedScoringAgent
from app.scoring.org_readiness_scorer import OrgReadinessScoringAgent
from app.scoring.urgency_scorer import UrgencyScoringAgent
from app.scoring.winnability_scorer import WinnabilityScoringAgent


def _fleet_operator_evidence() -> list[EvidenceItem]:
    """Evidence shaped like the reported case: a public transit / bus
    fleet operator undergoing EV electrification, not a software company."""
    return [
        EvidenceItem(
            signal_label="EV fleet",
            excerpt="The operator currently runs 100 EV buses across its network as part of a fleet electrification program",
            source="News",
            confidence=0.9,
        ),
        EvidenceItem(
            signal_label="New EV order",
            excerpt="The company placed an order for 25 additional EV buses to expand its electric fleet",
            source="News",
            confidence=0.9,
        ),
        EvidenceItem(
            signal_label="Network expansion",
            excerpt="Announced an expansion of service into three new metro areas this quarter",
            source="News",
            confidence=0.85,
        ),
        EvidenceItem(
            signal_label="Technology focus",
            excerpt="Leadership highlighted a strong technology focus, including a new digital transformation initiative for fleet operations",
            source="Website",
            confidence=0.8,
        ),
        EvidenceItem(
            signal_label="Fleet size",
            excerpt="The company operates a total fleet of over 1,200 vehicles nationwide",
            source="Company Profile",
            confidence=0.85,
        ),
        EvidenceItem(
            signal_label="Hiring volume",
            excerpt="Currently has 238 job vacancies posted across operations and maintenance roles",
            source="Jobs",
            confidence=0.9,
        ),
        EvidenceItem(
            signal_label="Company profile",
            excerpt="The company is a national operator with multi-site operations across 12 states",
            source="Company Profile",
            confidence=0.85,
        ),
    ]


@pytest.mark.asyncio
async def test_need_scorer_recognizes_electrification_and_modernization_evidence():
    evidence = _fleet_operator_evidence()
    result = await NeedScoringAgent().score("fleetco.example", evidence)
    assert result.score > 0
    assert result.confidence > 0
    assert result.reasons  # traceable back to specific evidence


@pytest.mark.asyncio
async def test_digital_maturity_scorer_recognizes_non_saas_technology_signals():
    evidence = _fleet_operator_evidence()
    result = await DigitalMaturityScoringAgent().score("fleetco.example", evidence)
    assert result.score > 0
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_org_readiness_scorer_recognizes_large_scale_hiring():
    evidence = _fleet_operator_evidence()
    result = await OrgReadinessScoringAgent().score("fleetco.example", evidence)
    assert result.score > 0
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_winnability_scorer_does_not_require_being_a_software_company():
    """A non-software operator must be able to score industry/organizational
    fit at all - the pre-fix keyword list only recognized "software
    company"/"saas"/"technology company" and excluded every other vertical
    by construction."""
    evidence = _fleet_operator_evidence()
    result = await WinnabilityScoringAgent().score("fleetco.example", evidence)
    assert result.score > 0


@pytest.mark.asyncio
async def test_urgency_scorer_recognizes_order_and_expansion_events():
    evidence = _fleet_operator_evidence()
    result = await UrgencyScoringAgent().score("fleetco.example", evidence)
    assert result.score > 0


def test_why_now_engine_treats_recent_ev_order_as_a_timing_trigger():
    """'Recent expansion/deployment events correctly trigger Why Now' -
    an EV order and a network expansion event, both dated within the
    freshness window, must produce a timing trigger."""
    from datetime import UTC, datetime, timedelta

    recent = datetime.now(UTC) - timedelta(days=5)
    evidence = [
        EvidenceItem(
            signal_label="New EV order",
            excerpt="The company placed an order for 25 additional EV buses",
            source="News",
            confidence=0.9,
            published_at=recent,
        ),
        EvidenceItem(
            signal_label="Network expansion",
            excerpt="Announced an expansion of service into three new metro areas",
            source="News",
            confidence=0.85,
            published_at=recent,
        ),
    ]
    result = WhyNowEngine().explain(evidence)
    assert result.has_timing_trigger
    assert result.data_sufficient
    assert len(result.triggers) >= 1


@pytest.mark.asyncio
async def test_missing_pillar_evidence_does_not_trigger_confidence_blind_penalty():
    """End-to-end: a pillar that found nothing (score=0, confidence=0)
    must not drag down the final purchase score via the Rule Engine's
    penalty adjustments - only a confidently-low pillar should."""
    from app.models.score import ScoreType
    from app.schemas.score import PillarScore

    pillars = [
        PillarScore(score_type=ScoreType.NEED, score=80, confidence=0.85, reasons=["strong need evidence"]),
        PillarScore(score_type=ScoreType.URGENCY, score=60, confidence=0.8, reasons=["recent order"]),
        # Capacity found literally nothing - this must read as "unknown",
        # not "confirmed low capacity", and must not halve the score.
        PillarScore(score_type=ScoreType.CAPACITY, score=0, confidence=0, reasons=[]),
        PillarScore(score_type=ScoreType.DIGITAL_MATURITY, score=55, confidence=0.7, reasons=["tech modernization"]),
        PillarScore(score_type=ScoreType.ORG_READINESS, score=50, confidence=0.75, reasons=["large hiring volume"]),
        PillarScore(score_type=ScoreType.WINNABILITY, score=40, confidence=0.6, reasons=["national operator"]),
    ]
    result = PurchaseAggregator().aggregate("fleetco.example", pillars)
    expected_unpenalized = 80 * 0.30 + 60 * 0.20 + 0 * 0.15 + 55 * 0.15 + 50 * 0.10 + 40 * 0.10
    assert result.purchase_score == pytest.approx(expected_unpenalized, abs=0.5)
    assert not result.disqualified
