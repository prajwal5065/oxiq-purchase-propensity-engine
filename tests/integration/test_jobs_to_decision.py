"""End-to-end proof that Jobs Collector evidence flows all the way through
the existing pipeline: JobsCollector -> RawSignal -> (simulated extraction,
since no live ANTHROPIC_API_KEY is available in tests) -> EvidenceNormalizer
-> DecisionIntelligenceEngine's Buying Intent, Why Now, and Decision Engine.

The "simulated extraction" step stands in for the Evidence Extractor's LLM
call (app/extraction/evidence_extractor.py) - it builds EvidenceItems the
same shape a real extraction would, directly from the JobsCollector's own
RawSignal payloads, so this test exercises every real, non-LLM stage of the
pipeline without requiring live API credentials.
"""
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from app.collectors.jobs_collector import JobsCollector
from app.decision.decision_intelligence_engine import DecisionIntelligenceEngine
from app.models.score import ScoreType
from app.schemas.decision import BuyingIntentLevel, DecisionPriority
from app.schemas.evidence import EvidenceItem
from app.schemas.explanation import (
    CollectorStatusReport,
    DisqualificationCategory,
    DisqualificationExplanation,
    EvidenceCoverage,
)
from app.schemas.score import PillarScore, PurchaseScoreResult
from app.schemas.signal import CollectorStatus
from app.services.evidence_normalizer import EvidenceNormalizer

GREENHOUSE_RESPONSE = {
    "jobs": [
        {
            "id": 1,
            "title": "Machine Learning Engineer",
            "updated_at": None,  # set per-test to keep freshness deterministic
            "location": {"name": "Remote"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
            "content": (
                "<p>Acme is expanding team headcount and hiring machine learning engineers "
                "to build and ship production models.</p>"
            ),
            "departments": [{"name": "AI"}],
        }
    ]
}


def _simulate_extraction(raw_signals) -> list[EvidenceItem]:
    """Stand-in for the LLM extraction step: for each job-posting RawSignal,
    build the EvidenceItem a real extraction run would plausibly produce -
    title as the label, the description as the excerpt, url/date/collector
    carried straight through."""
    items = []
    for signal in raw_signals:
        payload = signal.payload
        published_at = datetime.fromisoformat(payload["posted_at"]) if payload.get("posted_at") else None
        items.append(
            EvidenceItem(
                signal_label=payload["title"],
                excerpt=payload["description_snippet"] or payload["title"],
                source=f"{payload['provider'].title()} Job Posting",
                confidence=0.85,
                url=signal.url,
                published_at=published_at,
            )
        )
    return items


def make_coverage() -> EvidenceCoverage:
    return EvidenceCoverage(
        sources_discovered=7,
        sources_attempted=7,
        sources_successful=7,
        sources_failed=0,
        sources_zero_results=0,
        sources_not_configured=0,
        evidence_items_extracted=1,
        evidence_items_accepted=1,
        coverage_percentage=0.95,
        collector_statuses=[
            CollectorStatusReport(source="jobs", status=CollectorStatus.SUCCESS, is_live=True, signal_count=1),
        ],
    )


def make_purchase_result() -> PurchaseScoreResult:
    return PurchaseScoreResult(
        company_domain="acme.com",
        pillar_scores=[PillarScore(score_type=ScoreType.NEED, score=75.0, confidence=0.8, reasons=[])],
        purchase_score=75.0,
        confidence=0.8,
        disqualified=False,
    )


def make_qualified_disqualification() -> DisqualificationExplanation:
    return DisqualificationExplanation(
        final_decision="qualified",
        category=DisqualificationCategory.NOT_DISQUALIFIED,
        primary_reason="Evidence supports proceeding.",
        confidence=0.8,
        recommended_next_action="proceed",
    )


@pytest.mark.asyncio
@respx.mock
async def test_job_evidence_reaches_buying_intent_why_now_and_decision(monkeypatch):
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_LIVE_JOBS", "true")

    now = datetime.now(UTC)
    response_body = GREENHOUSE_RESPONSE.copy()
    response_body["jobs"][0]["updated_at"] = (now - timedelta(days=2)).isoformat()

    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
        return_value=httpx.Response(200, json=response_body)
    )
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(404))

    # Stage 1: JobsCollector -> RawSignal
    collector_result = await JobsCollector().collect("acme.com")
    assert collector_result.resolved_status == CollectorStatus.SUCCESS
    assert len(collector_result.signals) == 1
    assert collector_result.signals[0].category == "ai_ml_hiring"

    # Stage 2: simulated extraction -> EvidenceItem (real LLM call substituted)
    extracted_items = _simulate_extraction(collector_result.signals)
    assert len(extracted_items) == 1

    # Stage 3: EvidenceNormalizer -> collector inferred, jobs subtype category inherited
    normalized = EvidenceNormalizer().normalize(raw_signals=collector_result.signals, items=extracted_items)
    job_evidence = normalized[0]
    assert job_evidence.collector == "jobs"
    assert job_evidence.category == "ai_ml_hiring"

    # Stage 4: Decision Intelligence -> Buying Intent, Why Now, Decision
    bundle = DecisionIntelligenceEngine().build(
        evidence=normalized,
        coverage=make_coverage(),
        purchase_result=make_purchase_result(),
        disqualification=make_qualified_disqualification(),
        pillar_explanations=[],
        overall_confidence=0.8,
    )

    # Buying Intent: "expanding" + "hiring a Machine Learning Engineer" matches
    # the existing MODERATE-strength keyword set, and the match is traceable
    # back to this exact job evidence item.
    assert bundle.recommendation.buying_intent.level in (BuyingIntentLevel.MODERATE, BuyingIntentLevel.STRONG)
    assert any(
        sig.evidence_id == job_evidence.id for sig in bundle.recommendation.buying_intent.matched_signals
    )

    # Why Now: a 2-day-old "expanding team" signal is fresh enough (<=90 days)
    # to count as a timing trigger, and cites the same job evidence.
    assert bundle.recommendation.why_now.has_timing_trigger is True
    assert bundle.recommendation.why_now.triggers[0].evidence_id == job_evidence.id
    assert bundle.recommendation.why_now.triggers[0].trigger_type == "hiring_spike"

    # Decision: qualified, evidence-backed company should never land on
    # INSUFFICIENT_DATA, and the why-now boost should be visible in the factors.
    assert bundle.recommendation.priority != DecisionPriority.INSUFFICIENT_DATA
    boost_factor = next(f for f in bundle.recommendation.factors if f.name == "why_now_boost")
    assert boost_factor.value > 0

    # Evidence Confidence / Source Reliability: jobs is a HIGH-reliability,
    # structured-API collector, same as GitHub.
    confidence_score = next(s for s in bundle.evidence_confidence if s.evidence_id == job_evidence.id)
    assert confidence_score.source_reliability == 1.0
    assert any(row.collector == "jobs" and row.tier == "high" for row in bundle.source_reliability)

    get_settings.cache_clear()
    monkeypatch.delenv("ENABLE_LIVE_JOBS", raising=False)


@pytest.mark.asyncio
@respx.mock
async def test_no_job_board_found_never_produces_negative_buying_intent_or_decision(monkeypatch):
    """The absence of a discoverable job board must not read as a negative
    signal anywhere downstream - buying intent and decision should reflect
    'no evidence from this source', not 'this company shows no hiring
    activity'."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_LIVE_JOBS", "true")

    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(return_value=httpx.Response(404))
    respx.get("https://api.lever.co/v0/postings/acme").mock(return_value=httpx.Response(404))

    collector_result = await JobsCollector().collect("acme.com")
    assert collector_result.resolved_status == CollectorStatus.NO_RESULTS
    assert collector_result.errors == []
    assert collector_result.signals == []

    # No evidence at all from Jobs in this scenario - Decision Intelligence
    # still needs other evidence to make a genuine (non-insufficient) call;
    # here we simulate a thin-coverage scenario end-to-end to prove the
    # insufficient-data guardrail, not a negative conclusion, is what fires.
    bundle = DecisionIntelligenceEngine().build(
        evidence=[],
        coverage=EvidenceCoverage(
            sources_discovered=7,
            sources_attempted=7,
            sources_successful=0,
            sources_failed=0,
            sources_zero_results=7,
            sources_not_configured=0,
            evidence_items_extracted=0,
            evidence_items_accepted=0,
            coverage_percentage=0.0,
            collector_statuses=[
                CollectorStatusReport(source="jobs", status=CollectorStatus.NO_RESULTS, is_live=True, signal_count=0),
            ],
        ),
        purchase_result=PurchaseScoreResult(
            company_domain="acme.com", pillar_scores=[], purchase_score=0.0, confidence=0.0, disqualified=False
        ),
        disqualification=DisqualificationExplanation(
            final_decision="insufficient_data",
            category=DisqualificationCategory.COLLECTION_FAILURE,
            primary_reason="No evidence collected from any source.",
            confidence=0.0,
            recommended_next_action="retry collection",
        ),
        pillar_explanations=[],
        overall_confidence=0.0,
    )

    assert bundle.recommendation.priority == DecisionPriority.INSUFFICIENT_DATA
    assert bundle.recommendation.buying_intent.level == BuyingIntentLevel.INSUFFICIENT_DATA

    get_settings.cache_clear()
    monkeypatch.delenv("ENABLE_LIVE_JOBS", raising=False)
