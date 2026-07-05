from app.domain.models import EmbeddedChunk, RepositoryIndex
from app.services.fake_embedding_provider import FakeEmbeddingProvider
from app.services.semantic_search_service import SemanticSearchService
from app.services.vector_store import VectorStore


def _embedded_chunk(
    chunk_id: str,
    content: str,
    embedding: list[float],
    file_path: str,
    source_type: str,
) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_id=chunk_id,
        file_path=file_path,
        extension=".py",
        start_line=1,
        end_line=10,
        content=content,
        source_type=source_type,
        embedding=embedding,
    )


def test_semantic_search_returns_relevant_chunk():
    vector_store = VectorStore()
    repository_index = RepositoryIndex(
        index_id="index-1",
        repository_path="/repo",
        total_chunks_indexed=3,
        embedding_model="fake-embedding-model",
    )
    vector_store.store_index(
        repository_index,
        [
            _embedded_chunk(
                "scanner",
                "repository scanner service",
                [1.0, 0.0, 0.0],
                "app/services/repository_scanner.py",
                "source",
            ),
            _embedded_chunk(
                "chunk",
                "chunking service implementation",
                [0.0, 1.0, 0.0],
                "app/services/chunking_service.py",
                "source",
            ),
            _embedded_chunk(
                "config",
                "core config settings",
                [0.0, 0.0, 1.0],
                "app/core/config.py",
                "source",
            ),
        ],
    )

    service = SemanticSearchService(
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=vector_store,
    )
    results = service.search("index-1", "Where is the chunking logic implemented?", top_k=1)

    assert len(results) == 1
    assert results[0].chunk_id == "chunk"
    assert results[0].source_type == "source"
    assert results[0].score == 1.0


def test_semantic_search_excludes_tests_when_requested():
    vector_store = VectorStore()
    repository_index = RepositoryIndex(
        index_id="index-1",
        repository_path="/repo",
        total_chunks_indexed=2,
        embedding_model="fake-embedding-model",
    )
    vector_store.store_index(
        repository_index,
        [
            _embedded_chunk(
                "test-chunk",
                "chunking service implementation",
                [0.0, 1.0, 0.0],
                "tests/test_chunking_service.py",
                "test",
            ),
            _embedded_chunk(
                "source-chunk",
                "chunking service implementation",
                [0.0, 0.95, 0.0],
                "app/services/chunking_service.py",
                "source",
            ),
        ],
    )

    service = SemanticSearchService(
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=vector_store,
    )

    with_tests = service.search(
        "index-1",
        "Where is the chunking logic implemented?",
        top_k=1,
        include_tests=True,
    )
    without_tests = service.search(
        "index-1",
        "Where is the chunking logic implemented?",
        top_k=1,
        include_tests=False,
    )

    assert with_tests[0].source_type == "test"
    assert without_tests[0].source_type == "source"
    assert without_tests[0].file_path == "app/services/chunking_service.py"
