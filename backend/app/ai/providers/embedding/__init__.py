from app.ai.providers.base import EmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    """Return the embedding provider selected by EMBEDDING_PROVIDER."""
    from app.core.config import settings

    if settings.embedding_provider == "local":
        from app.ai.providers.embedding.local_provider import LocalEmbeddingProvider
        return LocalEmbeddingProvider()
    if settings.embedding_provider == "openai":
        from app.ai.providers.embedding.local_provider import OpenAIEmbeddingProvider
        return OpenAIEmbeddingProvider()
    from app.ai.providers.embedding.mock_provider import MockEmbeddingProvider
    return MockEmbeddingProvider()
