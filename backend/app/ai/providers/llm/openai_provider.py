"""
OpenAI LLM Provider — connects to OpenAI's API (or any OpenAI-compatible endpoint).

Requires LLM_API_KEY in .env. Set LLM_BASE_URL for alternative providers
(Together AI, Groq, Ollama, etc.).
"""

import json

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.providers.base import LLMMessage, LLMProvider, LLMResponse
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("openai_llm")


class OpenAILLMProvider(LLMProvider):
    """OpenAI (and OpenAI-compatible) LLM provider."""

    def __init__(self) -> None:
        client_kwargs: dict = {"api_key": settings.llm_api_key}
        if settings.llm_base_url:
            client_kwargs["base_url"] = settings.llm_base_url
        self._client = AsyncOpenAI(**client_kwargs)
        self._model = settings.llm_model
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens
        logger.info("OpenAI LLM provider initialized", model=self._model)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Call OpenAI chat completions API with retry logic."""
        oai_messages = [{"role": m.role, "content": m.content} for m in messages]

        kwargs: dict = {
            "model": self._model,
            "messages": oai_messages,
            "temperature": temperature if temperature is not None else self._temperature,
            "max_tokens": max_tokens if max_tokens is not None else self._max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def complete_json(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Call OpenAI with JSON mode enforced. Returns parsed dict."""
        response = await self.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from LLM", error=str(e), content=response.content[:200])
            raise ValueError(f"LLM returned non-JSON output: {e}") from e
