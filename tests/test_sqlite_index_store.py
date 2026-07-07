from datetime import datetime, timezone

import pytest

from app.core.database import init_database
from app.core.errors import IndexNotFoundError
from app.domain.models import EmbeddedChunk, RepositoryIndex
from app.services.sqlite_index_store import SQLiteIndexStore
from app.utils.source_type import SOURCE_TYPE_SOURCE, SOURCE_TYPE_TEST


def _repository_index(**overrides) -> RepositoryIndex:
    values = {
        "index_id": "index-1",
        "repository_path": "/repo",
        "total_chunks_indexed": 1,
        "embedding_model": "fake",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    values.update(overrides)
    return RepositoryIndex(**values)


def _embedded_chunk(
    chunk_id: str,
    content: str,
    embedding: list[float],
    file_path: str | None = None,
    source_type: str = "other",
) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_id=chunk_id,
        file_path=file_path or f"{chunk_id}.txt",
        extension=".txt",
        start_line=1,
        end_line=1,
        content=content,
        source_type=source_type,
        embedding=embedding,
    )


def test_init_database_creates_tables(sqlite_db_path):
    init_database(sqlite_db_path)

    store = SQLiteIndexStore(sqlite_db_path)
    assert store.list_indexes() == []


def test_store_and_get_index(index_store):
    repository_index = _repository_index(total_chunks_indexed=1)
    index_store.store_index(
        repository_index,
        [_embedded_chunk("only", "config values", [0.0, 0.0, 1.0])],
    )

    loaded = index_store.get_index("index-1")

    assert loaded.index_id == "index-1"
    assert loaded.repository_path == "/repo"
    assert loaded.created_at == repository_index.created_at


def test_list_indexes(index_store):
    index_store.store_index(
        _repository_index(index_id="index-a", total_chunks_indexed=1),
        [_embedded_chunk("a", "a", [1.0, 0.0, 0.0])],
    )
    index_store.store_index(
        _repository_index(index_id="index-b", total_chunks_indexed=1),
        [_embedded_chunk("b", "b", [0.0, 1.0, 0.0])],
    )

    indexes = index_store.list_indexes()

    assert {index.index_id for index in indexes} == {"index-a", "index-b"}


def test_delete_index_cascades_chunks(index_store):
    index_store.store_index(
        _repository_index(total_chunks_indexed=1),
        [_embedded_chunk("only", "config values", [0.0, 0.0, 1.0])],
    )

    index_store.delete_index("index-1")

    with pytest.raises(IndexNotFoundError):
        index_store.get_index("index-1")


def test_search_returns_highest_similarity_first(index_store):
    index_store.store_index(
        _repository_index(total_chunks_indexed=3),
        [
            _embedded_chunk("scanner", "scanner logic", [1.0, 0.0, 0.0]),
            _embedded_chunk("chunk", "chunk logic", [0.0, 1.0, 0.0]),
            _embedded_chunk("config", "config logic", [0.0, 0.0, 1.0]),
        ],
    )

    results = index_store.search("index-1", [0.0, 1.0, 0.0], top_k=3)

    assert results[0].chunk_id == "chunk"
    assert results[0].score == pytest.approx(1.0)
    assert results[1].score < results[0].score


def test_search_include_tests_false_excludes_test_chunks(index_store):
    index_store.store_index(
        _repository_index(total_chunks_indexed=2),
        [
            _embedded_chunk(
                "test-chunk",
                "chunk logic",
                [0.0, 1.0, 0.0],
                file_path="tests/test_chunk.py",
                source_type=SOURCE_TYPE_TEST,
            ),
            _embedded_chunk(
                "source-chunk",
                "chunk logic",
                [0.0, 0.95, 0.0],
                file_path="app/chunk.py",
                source_type=SOURCE_TYPE_SOURCE,
            ),
        ],
    )

    results = index_store.search(
        "index-1",
        [0.0, 1.0, 0.0],
        top_k=1,
        include_tests=False,
    )

    assert len(results) == 1
    assert results[0].source_type == SOURCE_TYPE_SOURCE


def test_search_raises_for_missing_index(index_store):
    with pytest.raises(IndexNotFoundError):
        index_store.search("missing-index", [1.0, 0.0, 0.0], top_k=1)


def test_persistence_survives_restart(sqlite_db_path):
    init_database(sqlite_db_path)
    store_a = SQLiteIndexStore(sqlite_db_path)
    store_a.store_index(
        _repository_index(total_chunks_indexed=1),
        [_embedded_chunk("chunk", "chunk logic", [0.0, 1.0, 0.0])],
    )

    store_b = SQLiteIndexStore(sqlite_db_path)
    results = store_b.search("index-1", [0.0, 1.0, 0.0], top_k=1)

    assert results[0].chunk_id == "chunk"
