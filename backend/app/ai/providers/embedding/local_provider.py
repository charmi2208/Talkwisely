"""
Local and OpenAI-compatible embedding providers.

LocalEmbeddingProvider runs all-MiniLM-L6-v2 through ONNX Runtime (bundled with
chromadb). It needs no API key; the ~80 MB model downloads on first use.
"""

import asyncio

from openai import AsyncOpenAI

from app.ai.providers.base import EmbeddingProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("embeddings")


class LocalEmbeddingProvider(EmbeddingProvider):
    """384-dimensional sentence embeddings computed on the CPU."""

    def __init__(self) -> None:
        try:
            from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        except ImportError as e:
            raise ImportError("Local embeddings need chromadb. Run: pip install chromadb") from e
        self._model = ONNXMiniLM_L6_V2()

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # ONNX inference is CPU-bound; keep it off the event loop
        vectors = await asyncio.to_thread(self._model, texts)
        return [[float(x) for x in v] for v in vectors]

    @property
    def dimension(self) -> int:
        return 384

    @property
    def provider_name(self) -> str:
        return "local-minilm"


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embeddings from an OpenAI-compatible /embeddings endpoint."""

    def __init__(self) -> None:
        kwargs: dict = {"api_key": settings.llm_api_key}
        if settings.llm_base_url:
            kwargs["base_url"] = settings.llm_base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = settings.embedding_model

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        res = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in res.data]

    @property
    def dimension(self) -> int:
        return settings.embedding_dimension

    @property
    def provider_name(self) -> str:
        return f"openai-{self._model}"
