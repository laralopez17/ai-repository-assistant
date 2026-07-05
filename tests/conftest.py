import pytest
from fastapi.testclient import TestClient

from app.api.routes import repositories as repositories_routes
from app.main import app
from app.services.embedding_factory import get_embedding_provider
from app.services.fake_embedding_provider import FakeEmbeddingProvider
from app.services.vector_store import VectorStore


@pytest.fixture
def fake_embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def vector_store() -> VectorStore:
    return VectorStore()


@pytest.fixture
def api_client(
    fake_embedding_provider: FakeEmbeddingProvider,
    vector_store: VectorStore,
) -> TestClient:
    app.dependency_overrides[get_embedding_provider] = lambda: fake_embedding_provider
    app.dependency_overrides[repositories_routes.get_vector_store] = lambda: vector_store
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
