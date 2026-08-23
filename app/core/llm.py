"""Central LLM calling service.

Configured to use Anthropic (Claude) by default, and automatically
fall back to Google Gemini when Anthropic fails or is unconfigured.
"""
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def generate_text(prompt: str, system: str | None = None, max_tokens: int = 256) -> str:
    """Generate text using configured LLM.

    Attempts to call Anthropic Claude first. If that raises an exception
    or is not configured, it falls back to Google Gemini.
    If both fail, it raises the last exception encountered.
    """
    settings = get_settings()
    last_exception = None

    # 1. Attempt Anthropic
    if settings.anthropic_api_key:
        try:
            import anthropic
            logger.info("llm.calling_anthropic", model=settings.anthropic_model)
            async with anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key) as client:
                response = await client.messages.create(
                    model=settings.anthropic_model,
                    max_tokens=max_tokens,
                    system=system or "",
                    messages=[{"role": "user", "content": prompt}],
                )
            logger.info("llm.anthropic_success")
            return response.content[0].text.strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "llm.anthropic_failed",
                error=str(exc),
                message="falling back to Gemini if available"
            )
            last_exception = exc

    # 2. Fallback to Gemini
    if settings.gemini_api_key:
        try:
            import google.genai as genai
            logger.info("llm.calling_gemini", model=settings.gemini_model)
            client = genai.Client(api_key=settings.gemini_api_key)

            # Map system instruction to google-genai schema format
            contents = []
            if system:
                contents.append({"role": "user", "parts": [{"text": system + "\n\n" + prompt}]})
            else:
                contents.append({"role": "user", "parts": [{"text": prompt}]})

            # google-genai is synchronous
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
            )
            logger.info("llm.gemini_success")
            return response.text.strip()
        except Exception as exc:  # noqa: BLE001
            logger.error("llm.gemini_failed", error=str(exc))
            last_exception = exc

    # 3. No successful calls
    if last_exception:
        raise last_exception

    raise RuntimeError("No LLM provider is configured (both ANTHROPIC_API_KEY and GEMINI_API_KEY are missing)")
