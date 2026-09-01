"""RECOVERX AI — LLM Provider Factory"""
from __future__ import annotations
import logging
from functools import lru_cache
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


_override_provider: Optional[LLMProvider] = None


def set_llm_provider(provider: Optional[LLMProvider]) -> None:
    """Explicitly set or clear an active LLM provider override (used for test isolation)."""
    global _override_provider
    _override_provider = provider
    get_llm_provider.cache_clear()


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """
    Return the configured LLM provider singleton.
    Priority: override → gemini → openai → mock (fallback)
    """
    global _override_provider
    if _override_provider is not None:
        return _override_provider

    from app.config import get_settings
    settings = get_settings()

    provider_name = settings.llm_provider.lower()

    # Try Gemini
    if provider_name == "gemini" and settings.gemini_api_key:
        try:
            from app.llm.gemini_provider import GeminiProvider
            p = GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
            logger.info(f"[LLM] Using {p.provider_name}")
            return p
        except Exception as exc:
            logger.warning(f"[LLM] Gemini init failed ({exc}), trying fallback...")

    # Try OpenAI
    if provider_name == "openai" and settings.openai_api_key:
        try:
            from app.llm.openai_provider import OpenAIProvider
            p = OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
            logger.info(f"[LLM] Using {p.provider_name}")
            return p
        except Exception as exc:
            logger.warning(f"[LLM] OpenAI init failed ({exc}), using mock...")

    # Auto-detect Gemini key even when provider=mock
    if settings.gemini_api_key and provider_name != "mock":
        try:
            from app.llm.gemini_provider import GeminiProvider
            p = GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
            logger.info(f"[LLM] Auto-detected Gemini key, using {p.provider_name}")
            return p
        except Exception:
            pass

    # Default: MockProvider
    from app.llm.mock_provider import MockProvider
    logger.info("[LLM] Using MockProvider (deterministic demo mode)")
    return MockProvider()
