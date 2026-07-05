from app.core.config import EMBEDDING_PROVIDER
from app.core.errors import UnsupportedProviderError
from app.services.embedding_provider import EmbeddingProvider
from app.services.fake_embedding_provider import FakeEmbeddingProvider
from app.services.gemini_embedding_provider import GeminiEmbeddingProvider
from app.services.openai_embedding_provider import OpenAIEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    if EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbeddingProvider()
    if EMBEDDING_PROVIDER == "gemini":
        return GeminiEmbeddingProvider()
    if EMBEDDING_PROVIDER == "fake":
        return FakeEmbeddingProvider()
    raise UnsupportedProviderError(
        f"Unsupported embedding provider: {EMBEDDING_PROVIDER}"
    )
