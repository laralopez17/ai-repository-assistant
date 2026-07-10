from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.errors import ChunkLimitExceededError, IndexNotFoundError
from app.services.chunking_service import ChunkingService
from app.services.content_extractor import ContentExtractor
from app.services.fake_embedding_provider import FakeEmbeddingProvider
from app.services.repository_indexer import RepositoryIndexer
from app.services.repository_scanner import RepositoryScanner
from app.services.sqlite_index_store import SQLiteIndexStore


@pytest.fixture
def indexer_setup(index_store) -> tuple[RepositoryIndexer, SQLiteIndexStore]:
    indexer = RepositoryIndexer(
        scanner=RepositoryScanner(),
        content_extractor=ContentExtractor(),
        chunking_service=ChunkingService(max_chars_per_chunk=12000),
        embedding_provider=FakeEmbeddingProvider(),
        index_store=index_store,
    )
    return indexer, index_store


def test_repository_indexer_creates_index(tmp_path: Path, indexer_setup):
    indexer, index_store = indexer_setup
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "chunking.py").write_text("chunk logic here\n", encoding="utf-8")
    (repo / "scanner.py").write_text("scanner logic here\n", encoding="utf-8")

    repository_index = indexer.index_repository(str(repo), 80, 10)

    assert repository_index.total_chunks_indexed == 2
    assert repository_index.embedding_model == "fake-embedding-model"
    assert repository_index.created_at
    index_store.get_index(repository_index.index_id)


def test_repository_indexer_raises_when_no_chunks(tmp_path: Path, indexer_setup):
    indexer, _ = indexer_setup
    repo = tmp_path / "empty-repo"
    repo.mkdir()

    with pytest.raises(ValueError, match="No chunks available"):
        indexer.index_repository(str(repo), 80, 10)


def test_repository_indexer_raises_when_chunk_limit_exceeded(
    tmp_path: Path,
    index_store,
):
    indexer = RepositoryIndexer(
        scanner=RepositoryScanner(),
        content_extractor=ContentExtractor(),
        chunking_service=ChunkingService(max_chars_per_chunk=12000),
        embedding_provider=FakeEmbeddingProvider(),
        index_store=index_store,
        max_chunks_to_embed=2,
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "one.py").write_text("chunk one\n", encoding="utf-8")
    (repo / "two.py").write_text("chunk two\n", encoding="utf-8")
    (repo / "three.py").write_text("chunk three\n", encoding="utf-8")

    with pytest.raises(ChunkLimitExceededError, match="exceeding the limit of 2"):
        indexer.index_repository(str(repo), 80, 10)
