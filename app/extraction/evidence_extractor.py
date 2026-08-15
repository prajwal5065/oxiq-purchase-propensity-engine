"""Evidence Extraction Layer.

Turns raw collector signals into grounded EvidenceItems. The LLM is
instructed - and the schema enforces - that it must never invent a fact:
every EvidenceItem requires a verbatim-derived excerpt, its source, and a
confidence score. Runs in stub mode (returns []) when ENABLE_LIVE_LLM is
off or GEMINI_API_KEY is unset.
"""
import json

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.evidence import EvidenceBatch, EvidenceItem
from app.schemas.signal import RawSignal

logger = get_logger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are an evidence extraction engine. You will be given raw text \
signals collected about a company from the public web (search results, website pages, tech \
detection, news, job postings).

Rules you MUST follow:
1. Only extract facts that are explicitly stated in the provided text. NEVER infer, guess, or \
   fabricate a fact that is not directly supported by the excerpt.
2. Every item you output must include the exact excerpt (a short verbatim quote or close \
   paraphrase) that supports it, the source name, and a confidence score between 0 and 1 \
   reflecting how directly the excerpt supports the claim.
3. If the raw signal includes a publish/event date (e.g. a news item's "published" field), copy \
   it into "published_at" as an ISO 8601 string. If no date is present or determinable, set \
   "published_at" to null. NEVER guess a date that isn't explicitly in the source data.
4. If a signal is ambiguous or weakly supported, either omit it or assign it a low confidence \
   (< 0.5). Do not round up confidence to make a signal look stronger than the text supports.
5. Return ONLY a JSON array of objects with keys: signal_label, excerpt, source, url, \
   confidence, published_at. No prose, no markdown fences.
"""


class EvidenceExtractor:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def extract(self, company_domain: str, raw_signals: list[RawSignal]) -> EvidenceBatch:
        if not self.settings.enable_live_llm or not self.settings.gemini_api_key:
            logger.info("evidence_extractor.stub_mode", domain=company_domain)
            return EvidenceBatch(company_domain=company_domain, items=[])

        if not raw_signals:
            return EvidenceBatch(company_domain=company_domain, items=[])

        try:
            import google.genai as genai

            client = genai.Client(api_key=self.settings.gemini_api_key)

            signals_payload = [s.model_dump() for s in raw_signals]
            user_content = (
                f"Company domain: {company_domain}\n\nRaw signals:\n"
                f"{json.dumps(signals_payload, default=str)}"
            )
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=[
                    {"role": "user", "parts": [{"text": EXTRACTION_SYSTEM_PROMPT + "\n\n" + user_content}]}
                ],
            )
            response_text = response.text
            items = self._parse_response(response_text)
            return EvidenceBatch(company_domain=company_domain, items=items)
        except Exception as exc:  # noqa: BLE001
            logger.error("evidence_extractor.failed", domain=company_domain, error=str(exc))
            return EvidenceBatch(company_domain=company_domain, items=[])

    @staticmethod
    def _parse_response(text: str) -> list[EvidenceItem]:
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            raw_items = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        items: list[EvidenceItem] = []
        for raw in raw_items:
            try:
                items.append(EvidenceItem(**raw))
            except Exception:  # noqa: BLE001 - a malformed date shouldn't sink an otherwise-good item
                raw_without_date = {k: v for k, v in raw.items() if k != "published_at"}
                try:
                    items.append(EvidenceItem(**raw_without_date))
                except Exception:  # noqa: BLE001 - still malformed, drop it
                    continue
        return items
