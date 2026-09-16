"""
OpenAI LLM Provider — connects to OpenAI's API (or any OpenAI-compatible endpoint).

Requires LLM_API_KEY in .env.local. Set LLM_BASE_URL for alternative providers
(Groq, Together AI, Ollama, etc.).
"""

import asyncio
import json

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
from tenacity import retry, retry_if_exception, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.ai.providers.base import LLMMessage, LLMProvider, LLMResponse
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("openai_llm")


def _is_retryable(exc: BaseException) -> bool:
    """Retry rate limits, network/server hiccups and rejected JSON — not bad requests in general."""
    if isinstance(exc, (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)):
        return True
    if isinstance(exc, BadRequestError):
        # Groq rejects JSON-mode replies that aren't valid JSON; a retry usually succeeds
        return "json_validate_failed" in str(exc)
    return False


_retry = retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)

# complete() already retries transport errors; this only re-asks when the reply isn't valid JSON
_retry_invalid_json = retry(
    retry=retry_if_exception_type(json.JSONDecodeError),
    stop=stop_after_attempt(2),
    reraise=True,
)


class OpenAILLMProvider(LLMProvider):
    """OpenAI (and OpenAI-compatible) LLM provider."""

    def __init__(self) -> None:
        if not settings.llm_api_key:
            raise ValueError("LLM_PROVIDER=openai needs LLM_API_KEY (set it in backend/.env.local)")
        client_kwargs: dict = {"api_key": settings.llm_api_key}
        if settings.llm_base_url:
            client_kwargs["base_url"] = settings.llm_base_url
        self._client = AsyncOpenAI(**client_kwargs)
        self._model = settings.llm_model
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens
        # The pipeline fans out several agents at once; cap it to stay under provider rate limits
        self._slots = asyncio.Semaphore(max(1, settings.llm_max_concurrency))
        logger.info("OpenAI-compatible LLM provider initialized", model=self._model, base_url=settings.llm_base_url or "openai")

    @property
    def provider_name(self) -> str:
        return "openai"

    async def aclose(self) -> None:
        """Close the HTTP pool while its event loop is still running."""
        await self._client.close()

    @property
    def model_name(self) -> str:
        return self._model

    @_retry
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Call the chat completions API with retry logic."""
        oai_messages = [{"role": m.role, "content": m.content} for m in messages]

        kwargs: dict = {
            "model": self._model,
            "messages": oai_messages,
            "temperature": temperature if temperature is not None else self._temperature,
            "max_tokens": max_tokens if max_tokens is not None else self._max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format
        if settings.llm_reasoning_effort:
            kwargs["reasoning_effort"] = settings.llm_reasoning_effort

        async with self._slots:
            response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )

    @_retry_invalid_json
    async def complete_json(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Call the API with JSON mode enforced. Returns the parsed dict."""
        response = await self.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON, retrying", content=response.content[:200])
            raise
        if not isinstance(parsed, dict):
            raise ValueError("LLM returned JSON that isn't an object")
        return parsed
