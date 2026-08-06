"""Analysis Orchestrator - the service-layer glue for phases 3-5:

    Signal Collection -> Evidence Extraction -> Scoring Agents

Phases 6-10 (Rule Engine, Purchase Aggregator, Recommendation Generator,
full REST surface, frontend) are not implemented yet; this service returns
per-pillar PillarScores and persists raw signals + evidence + scores so
those later phases have real data to build on.
"""
import asyncio

from app.collectors.news_collector import NewsCollector
from app.collectors.search_collector import SearchCollector
from app.collectors.tech_collector import TechCollector
from app.collectors.website_collector import WebsiteCollector
from app.core.logging import get_logger
from app.extraction.evidence_extractor import EvidenceExtractor
from app.models.evidence import Evidence as EvidenceModel
from app.models.score import Score as ScoreModel
from app.models.signal import Signal as SignalModel
from app.repositories.company_repository import CompanyRepository
from app.schemas.evidence import EvidenceItem
from app.schemas.score import PillarScore
from app.schemas.signal import CollectorResult, RawSignal
from app.scoring import ALL_SCORING_AGENTS

logger = get_logger(__name__)


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

    async def analyze(self, company_domain: str, company_name: str | None = None) -> list[PillarScore]:
        company = await self.repo.get_or_create(domain=company_domain, name=company_name or company_domain)

        collector_results = await self._run_collectors(company_domain)
        raw_signals = [s for result in collector_results for s in result.signals]
        await self.repo.add_signals(company, self._to_signal_models(raw_signals))

        evidence_batch = await self.extractor.extract(company_domain, raw_signals)
        await self.repo.add_evidence(company, self._to_evidence_models(evidence_batch.items))

        pillar_scores = await self._run_scoring_agents(company_domain, evidence_batch.items)
        await self.repo.add_scores(company, self._to_score_models(pillar_scores))

        await self.repo.commit()
        logger.info(
            "analysis.completed",
            domain=company_domain,
            signals=len(raw_signals),
            evidence=len(evidence_batch.items),
        )
        return pillar_scores

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
