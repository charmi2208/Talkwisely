"""
Mock & OpenAI Embedding Providers.

Provides vector embeddings for transcripts and knowledge documents.
If an API key is absent, uses a deterministic hash-based mock embedding provider.
"""

import math
import hashlib
from app.ai.providers.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Generates 384-dimensional deterministic mock embeddings from text hash."""

    def __init__(self, dimension: int = 384):
        self._dim = dimension

    async def embed_text(self, text: str) -> list[float]:
        return self._hash_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vector(t) for t in texts]

    def _hash_vector(self, text: str) -> list[float]:
        # Generate pseudo-random vector deterministically from md5 hash
        vector = []
        md5 = hashlib.md5(text.encode("utf-8")).digest()
        for i in range(self._dim):
            byte_val = md5[i % len(md5)]
            val = (byte_val / 255.0) * 2.0 - 1.0 + (math.sin(i + len(text)) * 0.1)
            vector.append(round(val, 6))
        # Normalize
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [round(x / norm, 6) for x in vector]

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider_name(self) -> str:
        return "mock"
