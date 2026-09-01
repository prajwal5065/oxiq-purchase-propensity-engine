"""Evidence Extraction Layer.

Turns raw collector signals into grounded EvidenceItems. The LLM is
instructed - and the schema enforces - that it must never invent a fact:
every EvidenceItem requires a verbatim-derived excerpt, its source, and a
confidence score. Runs in stub mode (returns []) when ENABLE_LIVE_LLM is
off or ANTHROPIC_API_KEY is unset.

Source/URL are not trusted from the LLM's own free-text output: it's
asked to report which raw signal (by index) it drew each item from, and
this module then overwrites `source`/`url` from that signal's own,
already-known-true `url` field. Relying on the model to correctly
transcribe a URL out of a large JSON blob it's also summarizing is
fragile - and was the actual cause of evidence showing generic sources
like "search"/"news" instead of the real outlet, even when the raw
signal (e.g. from Tavily) carried a concrete URL the whole time.
"""
import json
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.evidence import EvidenceBatch, EvidenceItem
from app.schemas.signal import RawSignal

logger = get_logger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are an evidence extraction engine. You will be given raw text \
signals collected about a company from the public web (search results, website pages, tech \
detection, news, job postings). Each signal in the input array has a "signal_index" field.

Rules you MUST follow:
1. Only extract facts that are explicitly stated in the provided text. NEVER infer, guess, or \
   fabricate a fact that is not directly supported by the excerpt.
2. Every item you output must include the exact excerpt (a short verbatim quote or close \
   paraphrase) that supports it, the "signal_index" of the raw signal it was drawn from, your \
   best guess at the source name (e.g. the publication or page it came from), and a confidence \
   score between 0 and 1 reflecting how directly the excerpt supports the claim.
3. If the raw signal includes a publish/event date (e.g. a news item's "published" field), copy \
   it into "published_at" as an ISO 8601 string. If no date is present or determinable, set \
   "published_at" to null. NEVER guess a date that isn't explicitly in the source data.
4. If a signal is ambiguous or weakly supported, either omit it or assign it a low confidence \
   (< 0.5). Do not round up confidence to make a signal look stronger than the text supports.
5. Return ONLY a JSON array of objects with keys: signal_label, excerpt, source, signal_index, \
   confidence, published_at. No prose, no markdown fences.
"""

# Source labels the extraction LLM tends to fall back on when it can't
# identify a specific outlet/page - not useful to a reader trying to judge
# provenance, so these are always replaced with the raw signal's actual
# URL/domain when one is known (see `_bind_source_and_url`).
_GENERIC_SOURCE_LABELS = {
    "search", "web search", "search result", "search results", "search engine",
    "search snippet", "google", "google search", "news", "news article",
    "the web", "internet", "internet search", "unknown",
}


class EvidenceExtractor:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def extract(self, company_domain: str, raw_signals: list[RawSignal]) -> EvidenceBatch:
        if not self.settings.enable_live_llm or (not self.settings.anthropic_api_key and not self.settings.gemini_api_key):
            logger.info("evidence_extractor.stub_mode", domain=company_domain)
            return EvidenceBatch(company_domain=company_domain, items=[])

        if not raw_signals:
            return EvidenceBatch(company_domain=company_domain, items=[])

        try:
            from app.core.llm import generate_text

            signals_payload = [{"signal_index": i, **s.model_dump()} for i, s in enumerate(raw_signals)]
            user_content = (
                f"Company domain: {company_domain}\n\nRaw signals:\n"
                f"{json.dumps(signals_payload, default=str)}"
            )
            
            response_text = await generate_text(
                prompt=user_content,
                system=EXTRACTION_SYSTEM_PROMPT,
                max_tokens=4096
            )
            items = self._parse_response(response_text, raw_signals)
            return EvidenceBatch(company_domain=company_domain, items=items)
        except Exception as exc:  # noqa: BLE001
            logger.error("evidence_extractor.failed", domain=company_domain, error=str(exc))
            return EvidenceBatch(company_domain=company_domain, items=[])

    @staticmethod
    def _parse_response(text: str, raw_signals: list[RawSignal]) -> list[EvidenceItem]:
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            raw_items = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        items: list[EvidenceItem] = []
        for raw in raw_items:
            raw = EvidenceExtractor._bind_source_and_url(raw, raw_signals)
            try:
                items.append(EvidenceItem(**raw))
            except Exception:  # noqa: BLE001 - a malformed date shouldn't sink an otherwise-good item
                raw_without_date = {k: v for k, v in raw.items() if k != "published_at"}
                try:
                    items.append(EvidenceItem(**raw_without_date))
                except Exception:  # noqa: BLE001 - still malformed, drop it
                    continue
        return items

    @staticmethod
    def _bind_source_and_url(raw: dict, raw_signals: list[RawSignal]) -> dict:
        """Overwrite `url` (always) and `source` (when the LLM only gave a
        generic category name) from the raw signal the LLM says it drew
        this item from - ground truth the model can't have gotten wrong,
        since it's copied from the signal itself, not re-typed by the LLM.
        """
        raw = dict(raw)
        index = raw.pop("signal_index", None)
        if not isinstance(index, int) or not (0 <= index < len(raw_signals)):
            return raw

        origin = raw_signals[index]
        if not origin.url:
            return raw

        raw["url"] = origin.url
        domain = EvidenceExtractor._domain_from_url(origin.url)
        current_source = str(raw.get("source") or "").strip()
        if domain and (not current_source or current_source.lower() in _GENERIC_SOURCE_LABELS):
            raw["source"] = domain
        return raw

    @staticmethod
    def _domain_from_url(url: str) -> str | None:
        try:
            netloc = urlparse(url).netloc
        except ValueError:
            return None
        return netloc.removeprefix("www.") or None
