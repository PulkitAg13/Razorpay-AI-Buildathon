"""
RECOVERX AI — Modern Gemini LLM Provider (google.genai SDK)
Includes resilient structured output parsing and temporary circuit breaker
to prevent cascade failure on rate-limit / quota exhaustion.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from app.llm.base import LLMProvider, LLMProviderError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    Modern Google GenAI SDK Client for Gemini models.
    Supports dynamic model switching, structured Pydantic validation,
    and automatic circuit breaker to preserve free tier / quota limits.
    """

    def __init__(self, api_key: str, model: str = "gemini-3.6-flash") -> None:
        self._api_key = api_key
        self._model = model
        self._circuit_open_until: float = 0.0
        self._cooldown_seconds: float = 60.0

        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
        except ImportError:
            raise LLMProviderError(
                "google-genai SDK not installed. Run: pip install google-genai"
            )

    @property
    def provider_name(self) -> str:
        return f"Gemini/{self._model}"

    @property
    def is_available(self) -> bool:
        """Returns False if circuit breaker is currently open."""
        return time.time() >= self._circuit_open_until

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        temperature: float = 0.1,
    ) -> T:
        # Check circuit breaker
        now = time.time()
        if now < self._circuit_open_until:
            remaining = int(self._circuit_open_until - now)
            raise LLMProviderError(
                f"Circuit open: Gemini unavailable for next {remaining}s. Using deterministic fallback mode."
            )

        from google.genai import types

        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        full_prompt = (
            f"{system_prompt}\n\n"
            f"IMPORTANT: Respond ONLY with valid JSON matching this schema:\n{schema_json}\n\n"
            f"{user_prompt}\n\nJSON response:"
        )

        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
        )

        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model,
                contents=full_prompt,
                config=config,
            )

            raw = (response.text or "").strip()
            # Extract JSON substring using regex
            json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
            if json_match:
                raw = json_match.group(0)

            data = json.loads(raw)
            return schema.model_validate(data)

        except Exception as exc:
            err_str = str(exc)
            # Trip circuit breaker on rate limit / 429 quota exhaustion / service unavailability
            if "429" in err_str or "quota" in err_str.lower() or "resourceexhausted" in err_str.lower():
                # Extract retry delay if available in error message
                cooldown = self._cooldown_seconds
                retry_match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str)
                if retry_match:
                    cooldown = max(10.0, float(retry_match.group(1)) + 2.0)
                
                self._circuit_open_until = time.time() + cooldown
                logger.warning(
                    f"[GeminiProvider] Quota/Rate limit encountered. Circuit open for {cooldown:.0f}s. "
                    "Routing requests to deterministic fallback mode."
                )
            else:
                logger.warning(f"[GeminiProvider] Generation failed: {err_str[:120]}")

            raise LLMProviderError(err_str) from exc
