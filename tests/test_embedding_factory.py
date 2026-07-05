from app.core.errors import EmbeddingProviderError
from app.services.embedding_factory import get_embedding_provider
from app.services.fake_embedding_provider import FakeEmbeddingProvider


def test_embedding_factory_returns_fake_provider(monkeypatch):
    monkeypatch.setattr("app.services.embedding_factory.EMBEDDING_PROVIDER", "fake")

    provider = get_embedding_provider()

    assert isinstance(provider, FakeEmbeddingProvider)
    assert provider.model_name == "fake-embedding-model"
