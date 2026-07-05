import pytest

from app.core.errors import IndexNotFoundError
from app.domain.models import EmbeddedChunk, RepositoryIndex
from app.services.vector_store import VectorStore, cosine_similarity


def test_cosine_similarity_for_identical_vectors():
    vector = [1.0, 0.0, 0.0]
    assert cosine_similarity(vector, vector) == pytest.approx(1.0)


def test_cosine_similarity_for_orthogonal_vectors():
    assert cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]) == pytest.approx(0.0)


def test_cosine_similarity_for_opposite_vectors():
    assert cosine_similarity([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]) == pytest.approx(-1.0)


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


def test_vector_store_returns_highest_similarity_first():
    store = VectorStore()
    repository_index = RepositoryIndex(
        index_id="index-1",
        repository_path="/repo",
        total_chunks_indexed=3,
        embedding_model="fake",
    )
    store.store_index(
        repository_index,
        [
            _embedded_chunk("scanner", "scanner logic", [1.0, 0.0, 0.0]),
            _embedded_chunk("chunk", "chunk logic", [0.0, 1.0, 0.0]),
            _embedded_chunk("config", "config logic", [0.0, 0.0, 1.0]),
        ],
    )

    results = store.search("index-1", [0.0, 1.0, 0.0])[:3]

    assert results[0].chunk_id == "chunk"
    assert results[0].score == pytest.approx(1.0)
    assert results[1].score < results[0].score


def test_vector_store_raises_for_missing_index():
    store = VectorStore()

    with pytest.raises(IndexNotFoundError):
        store.search("missing-index", [1.0, 0.0, 0.0])


def test_vector_store_has_index():
    store = VectorStore()
    repository_index = RepositoryIndex(
        index_id="index-1",
        repository_path="/repo",
        total_chunks_indexed=1,
        embedding_model="fake",
    )
    store.store_index(
        repository_index,
        [_embedded_chunk("only", "config values", [0.0, 0.0, 1.0])],
    )

    assert store.has_index("index-1") is True
    assert store.has_index("missing") is False
