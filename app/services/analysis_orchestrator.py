"""Analysis Orchestrator - the full pipeline:

    Signal Collection -> Evidence Extraction -> Scoring Agents
    -> Rule Engine -> Purchase Aggregator -> Recommendation Generator

Phase 10 (frontend) and richer phase-9 API surface aside, this is now the
complete flow from the architecture diagram.
"""
import asyncio

from app.aggregation.purchase_aggregator import PurchaseAggregator
from app.collectors.news_collector import NewsCollector
from app.collectors.search_collector import SearchCollector
from app.collectors.tech_collector import TechCollector
from app.collectors.website_collector import WebsiteCollector
from app.core.logging import get_logger
from app.extraction.evidence_extractor import EvidenceExtractor
from app.models.evidence import Evidence as EvidenceModel
from app.models.recommendation import Recommendation as RecommendationModel
from app.models.score import Score as ScoreModel
from app.models.score import ScoreType
from app.models.signal import Signal as SignalModel
from app.recommendation.generator import RecommendationGenerator
from app.repositories.company_repository import CompanyRepository
from app.schemas.evidence import EvidenceItem
from app.schemas.recommendation import RecommendationResult
from app.schemas.score import PillarScore, PurchaseScoreResult
from app.schemas.signal import CollectorResult, RawSignal
from app.scoring import ALL_SCORING_AGENTS

logger = get_logger(__name__)


class AnalysisResult:
    def __init__(self, purchase_result: PurchaseScoreResult, recommendation: RecommendationResult) -> None:
        self.purchase_result = purchase_result
        self.recommendation = recommendation


class AnalysisOrchestrator:
    def __init__(self, company_repository: CompanyRepository) -> None:
        self.repo = company_repository
        self.collectors = [
            SearchCollector(),
            WebsiteCollector(),
            TechCollector(),
            NewsCollector(),
        ]
        self.extractor = EvidenceExtractor()
        self.aggregator = PurchaseAggregator()
        self.recommender = RecommendationGenerator()

    async def analyze(self, company_domain: str, company_name: str | None = None) -> AnalysisResult:
        company = await self.repo.get_or_create(domain=company_domain, name=company_name or company_domain)

        collector_results = await self._run_collectors(company_domain)
        raw_signals = [s for result in collector_results for s in result.signals]
        await self.repo.add_signals(company, self._to_signal_models(raw_signals))

        evidence_batch = await self.extractor.extract(company_domain, raw_signals)
        await self.repo.add_evidence(company, self._to_evidence_models(evidence_batch.items))

        pillar_scores = await self._run_scoring_agents(company_domain, evidence_batch.items)
        await self.repo.add_scores(company, self._to_score_models(pillar_scores))

        purchase_result = self.aggregator.aggregate(
            company_domain=company_domain, pillar_scores=pillar_scores, industry=company.industry
        )
        await self.repo.add_scores(company, [self._to_purchase_score_model(purchase_result)])

        recommendation = await self.recommender.generate(company_domain, purchase_result, evidence_batch.items)
        await self.repo.add_recommendation(company, self._to_recommendation_model(recommendation))

        await self.repo.commit()
        logger.info(
            "analysis.completed",
            domain=company_domain,
            signals=len(raw_signals),
            evidence=len(evidence_batch.items),
            purchase_score=purchase_result.purchase_score,
            disqualified=purchase_result.disqualified,
        )
        return AnalysisResult(purchase_result=purchase_result, recommendation=recommendation)

    async def _run_collectors(self, company_domain: str) -> list[CollectorResult]:
        return await asyncio.gather(*(c.collect(company_domain) for c in self.collectors))

    async def _run_scoring_agents(
        self, company_domain: str, evidence: list[EvidenceItem]
    ) -> list[PillarScore]:
        agents = [agent_cls() for agent_cls in ALL_SCORING_AGENTS]
        return await asyncio.gather(*(a.score(company_domain, evidence) for a in agents))

    @staticmethod
    def _to_signal_models(raw_signals: list[RawSignal]) -> list[SignalModel]:
        return [
            SignalModel(source=s.source, category=s.category, payload=s.payload, url=s.url)
            for s in raw_signals
        ]

    @staticmethod
    def _to_evidence_models(items: list[EvidenceItem]) -> list[EvidenceModel]:
        return [
            EvidenceModel(
                signal_label=item.signal_label,
                excerpt=item.excerpt,
                source=item.source,
                url=str(item.url) if item.url else None,
                confidence=item.confidence,
            )
            for item in items
        ]

    @staticmethod
    def _to_score_models(pillar_scores: list[PillarScore]) -> list[ScoreModel]:
        return [
            ScoreModel(
                score_type=p.score_type,
                value=p.score,
                confidence=p.confidence,
                reasons=p.reasons,
            )
            for p in pillar_scores
        ]

    @staticmethod
    def _to_purchase_score_model(purchase_result: PurchaseScoreResult) -> ScoreModel:
        return ScoreModel(
            score_type=ScoreType.PURCHASE_PROPENSITY,
            value=purchase_result.purchase_score,
            confidence=purchase_result.confidence,
            reasons=purchase_result.evidence_summary,
        )

    @staticmethod
    def _to_recommendation_model(recommendation: RecommendationResult) -> RecommendationModel:
        return RecommendationModel(
            executive_summary=recommendation.executive_summary,
            fit_reasons=recommendation.fit_reasons,
            top_buying_signals=recommendation.top_buying_signals,
            top_risks=recommendation.top_risks,
            suggested_approach=recommendation.suggested_approach,
            contact_priority=recommendation.contact_priority,
            solution_match=recommendation.solution_match,
        )
