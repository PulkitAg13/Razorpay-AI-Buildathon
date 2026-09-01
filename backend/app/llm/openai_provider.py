"""RECOVERX AI — OpenAI LLM Provider"""
from __future__ import annotations
import json, logging
from typing import Type, TypeVar
from pydantic import BaseModel
from app.llm.base import LLMProvider, LLMProviderError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._model = model
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key)
        except ImportError:
            raise LLMProviderError("openai not installed. Run: pip install openai")

    @property
    def provider_name(self) -> str:
        return f"OpenAI/{self._model}"

    async def generate_structured(
        self, system_prompt: str, user_prompt: str,
        schema: Type[T], temperature: float = 0.1,
    ) -> T:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": f"{system_prompt}\n\nAlways respond with valid JSON matching the requested schema."},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return schema.model_validate(data)
        except Exception as exc:
            logger.warning(f"[OpenAIProvider] Generation failed: {exc}")
            raise LLMProviderError(str(exc)) from exc
