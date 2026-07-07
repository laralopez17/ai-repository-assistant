import pytest
from fastapi.testclient import TestClient

from app.api.routes import repositories as repositories_routes
from app.core.database import init_database
from app.main import app
from app.services.embedding_factory import get_embedding_provider
from app.services.fake_embedding_provider import FakeEmbeddingProvider
from app.services.fake_llm_provider import FakeLLMProvider
from app.services.llm_provider_factory import get_llm_provider
from app.services.sqlite_index_store import SQLiteIndexStore


@pytest.fixture
def sqlite_db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def index_store(sqlite_db_path):
    init_database(sqlite_db_path)
    return SQLiteIndexStore(sqlite_db_path)


@pytest.fixture
def fake_embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def fake_llm_provider() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def api_client(
    fake_embedding_provider: FakeEmbeddingProvider,
    fake_llm_provider: FakeLLMProvider,
    index_store: SQLiteIndexStore,
) -> TestClient:
    app.dependency_overrides[get_embedding_provider] = lambda: fake_embedding_provider
    app.dependency_overrides[get_llm_provider] = lambda: fake_llm_provider
    app.dependency_overrides[repositories_routes.get_index_store] = lambda: index_store
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
