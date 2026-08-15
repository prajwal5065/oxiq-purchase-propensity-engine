"""Recommendation Generator.

Turns a PurchaseScoreResult + its underlying evidence into something a
salesperson can act on. The bullet-point fields (fit_reasons,
top_buying_signals, top_risks) are built deterministically straight from
pillar reasons - no LLM involved, so they can never contain an invented
fact. Only the prose fields (executive_summary, suggested_approach) use
Gemini (Google), and only when ENABLE_LIVE_LLM + GEMINI_API_KEY are set; otherwise a
deterministic template covers the same ground.

`solution_match` ("best OxiQ offering") is left unset - it requires a
product/offering catalog that hasn't been provided yet. Wiring it in later
only means filling in `_match_solution` below.
"""
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.evidence import EvidenceItem
from app.schemas.recommendation import RecommendationResult
from app.schemas.score import PillarScore, PurchaseScoreResult

logger = get_logger(__name__)

HIGH_PRIORITY_THRESHOLD = 70.0
MEDIUM_PRIORITY_THRESHOLD = 40.0
WEAK_PILLAR_THRESHOLD = 30.0
STRONG_PILLAR_THRESHOLD = 50.0


class RecommendationGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate(
        self,
        company_domain: str,
        purchase_result: PurchaseScoreResult,
        evidence: list[EvidenceItem],
    ) -> RecommendationResult:
        contact_priority = self._contact_priority(purchase_result)
        fit_reasons = self._fit_reasons(purchase_result.pillar_scores)
        top_risks = self._top_risks(purchase_result)
        top_buying_signals = purchase_result.evidence_summary[:5]

        executive_summary, suggested_approach = await self._generate_prose(
            company_domain, purchase_result, fit_reasons, top_risks
        )

        return RecommendationResult(
            executive_summary=executive_summary,
            fit_reasons=fit_reasons,
            top_buying_signals=top_buying_signals,
            top_risks=top_risks,
            suggested_approach=suggested_approach,
            contact_priority=contact_priority,
            solution_match=self._match_solution(purchase_result),
        )

    def _contact_priority(self, purchase_result: PurchaseScoreResult) -> str:
        if purchase_result.disqualified:
            return "low"
        if purchase_result.purchase_score >= HIGH_PRIORITY_THRESHOLD:
            return "high"
        if purchase_result.purchase_score >= MEDIUM_PRIORITY_THRESHOLD:
            return "medium"
        return "low"

    @staticmethod
    def _fit_reasons(pillar_scores: list[PillarScore]) -> list[str]:
        reasons: list[str] = []
        for pillar in sorted(pillar_scores, key=lambda p: p.score, reverse=True):
            if pillar.score >= STRONG_PILLAR_THRESHOLD and pillar.reasons:
                reasons.append(f"{pillar.score_type.value.replace('_', ' ').title()}: {pillar.reasons[0]}")
        return reasons[:5]

    @staticmethod
    def _top_risks(purchase_result: PurchaseScoreResult) -> list[str]:
        if purchase_result.disqualified and purchase_result.disqualified_reason:
            return [purchase_result.disqualified_reason]
        risks: list[str] = []
        for pillar in purchase_result.pillar_scores:
            if pillar.score < WEAK_PILLAR_THRESHOLD:
                label = pillar.score_type.value.replace("_", " ").title()
                risks.append(f"Weak {label} ({pillar.score:.0f}/100) - little to no supporting evidence")
        return risks[:5]

    @staticmethod
    def _match_solution(purchase_result: PurchaseScoreResult) -> str | None:  # noqa: ARG004
        return None

    async def _generate_prose(
        self,
        company_domain: str,
        purchase_result: PurchaseScoreResult,
        fit_reasons: list[str],
        top_risks: list[str],
    ) -> tuple[str, str]:
        if self.settings.enable_live_llm and self.settings.gemini_api_key:
            try:
                return await self._generate_prose_live(company_domain, purchase_result, fit_reasons, top_risks)
            except Exception as exc:  # noqa: BLE001
                logger.error("recommendation_generator.llm_failed", domain=company_domain, error=str(exc))

        return self._generate_prose_stub(company_domain, purchase_result, fit_reasons, top_risks)

    @staticmethod
    def _generate_prose_stub(
        company_domain: str,
        purchase_result: PurchaseScoreResult,
        fit_reasons: list[str],
        top_risks: list[str],
    ) -> tuple[str, str]:
        if purchase_result.disqualified:
            summary = (
                f"{company_domain} is disqualified from active pursuit: "
                f"{purchase_result.disqualified_reason}"
            )
            approach = "Do not prioritize outreach until disqualifying conditions change."
            return summary, approach

        summary_parts = [
            f"{company_domain} scores {purchase_result.purchase_score:.0f}/100 on purchase "
            f"propensity (confidence {purchase_result.confidence:.0%})."
        ]
        if fit_reasons:
            summary_parts.append(f"Strongest signal: {fit_reasons[0]}.")
        if top_risks:
            summary_parts.append(f"Main gap: {top_risks[0]}.")
        summary = " ".join(summary_parts)

        if purchase_result.purchase_score >= HIGH_PRIORITY_THRESHOLD:
            approach = (
                "Prioritize outreach now - lead with the strongest signal above and involve "
                "an AE within the week."
            )
        elif purchase_result.purchase_score >= MEDIUM_PRIORITY_THRESHOLD:
            approach = "Add to a nurture sequence and monitor for fresh urgency signals before a direct pitch."
        else:
            approach = "Deprioritize for now; revisit if new funding, hiring, or product signals appear."

        return summary, approach

    @staticmethod
    async def _generate_prose_live(
        company_domain: str,
        purchase_result: PurchaseScoreResult,
        fit_reasons: list[str],
        top_risks: list[str],
    ) -> tuple[str, str]:
        import google.genai as genai

        settings = get_settings()
        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = (
            f"Company: {company_domain}\n"
            f"Purchase score: {purchase_result.purchase_score}/100 "
            f"(confidence {purchase_result.confidence})\n"
            f"Fit reasons: {fit_reasons}\n"
            f"Risks: {top_risks}\n"
        )
        system_instruction = (
            "You write a short, grounded sales brief from the structured facts you're given. "
            "Only reference the fit reasons and risks provided - never invent a fact, statistic, "
            "or claim that isn't in the input. Return exactly two lines: "
            "'SUMMARY: <2-3 sentences>' then 'APPROACH: <1-2 sentences>'."
        )
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[{"role": "user", "parts": [{"text": system_instruction + "\n\n" + prompt}]}],
        )
        text = response.text.strip()

        summary, approach = "", ""
        for line in text.splitlines():
            if line.startswith("SUMMARY:"):
                summary = line.removeprefix("SUMMARY:").strip()
            elif line.startswith("APPROACH:"):
                approach = line.removeprefix("APPROACH:").strip()

        if not summary or not approach:
            return RecommendationGenerator._generate_prose_stub(
                company_domain, purchase_result, fit_reasons, top_risks
            )
        return summary, approach
