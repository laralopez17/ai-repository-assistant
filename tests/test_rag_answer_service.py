from app.domain.models import EmbeddedChunk, RepositoryIndex, SearchResult
from app.services.fake_embedding_provider import FakeEmbeddingProvider
from app.services.fake_llm_provider import FakeLLMProvider, INSUFFICIENT_CONTEXT_ANSWER
from app.services.rag_answer_service import RAGAnswerService
from app.services.semantic_search_service import SemanticSearchService
from app.services.vector_store import VectorStore
from app.utils.source_type import SOURCE_TYPE_SOURCE, SOURCE_TYPE_TEST


def _embedded_chunk(
    file_path: str,
    content: str,
    embedding: list[float],
    source_type: str,
) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_id=f"{file_path}::chunk-000",
        file_path=file_path,
        extension=".py",
        start_line=1,
        end_line=10,
        content=content,
        source_type=source_type,
        embedding=embedding,
    )


def _build_service(vector_store: VectorStore) -> RAGAnswerService:
    return RAGAnswerService(
        semantic_search_service=SemanticSearchService(
            embedding_provider=FakeEmbeddingProvider(),
            vector_store=vector_store,
        ),
        llm_provider=FakeLLMProvider(),
    )


def test_rag_answer_service_returns_answer_with_sources():
    vector_store = VectorStore()
    vector_store.store_index(
        RepositoryIndex(
            index_id="index-1",
            repository_path="/repo",
            total_chunks_indexed=2,
            embedding_model="fake-embedding-model",
        ),
        [
            _embedded_chunk(
                "tests/test_chunking_service.py",
                "chunking service implementation",
                [0.0, 1.0, 0.0],
                SOURCE_TYPE_TEST,
            ),
            _embedded_chunk(
                "app/services/chunking_service.py",
                "chunking service implementation",
                [0.0, 0.95, 0.0],
                SOURCE_TYPE_SOURCE,
            ),
        ],
    )

    service = _build_service(vector_store)
    result = service.answer(
        "index-1",
        "Where is the chunking logic implemented?",
        top_k=1,
        include_tests=True,
    )

    assert "tests/test_chunking_service.py" in result.answer
    assert len(result.sources) == 1
    assert result.sources[0].file_path == "tests/test_chunking_service.py"


def test_rag_answer_service_excludes_tests_when_requested():
    vector_store = VectorStore()
    vector_store.store_index(
        RepositoryIndex(
            index_id="index-1",
            repository_path="/repo",
            total_chunks_indexed=2,
            embedding_model="fake-embedding-model",
        ),
        [
            _embedded_chunk(
                "tests/test_chunking_service.py",
                "chunking service implementation",
                [0.0, 1.0, 0.0],
                SOURCE_TYPE_TEST,
            ),
            _embedded_chunk(
                "app/services/chunking_service.py",
                "chunking service implementation",
                [0.0, 0.95, 0.0],
                SOURCE_TYPE_SOURCE,
            ),
        ],
    )

    service = _build_service(vector_store)
    result = service.answer(
        "index-1",
        "Where is the chunking logic implemented?",
        top_k=1,
        include_tests=False,
    )

    assert result.sources[0].source_type == SOURCE_TYPE_SOURCE
    assert result.sources[0].file_path == "app/services/chunking_service.py"


def test_rag_answer_service_returns_insufficient_context_when_no_chunks():
    vector_store = VectorStore()
    vector_store.store_index(
        RepositoryIndex(
            index_id="index-1",
            repository_path="/repo",
            total_chunks_indexed=1,
            embedding_model="fake-embedding-model",
        ),
        [
            _embedded_chunk(
                "tests/test_chunking_service.py",
                "chunking service implementation",
                [0.0, 1.0, 0.0],
                SOURCE_TYPE_TEST,
            ),
        ],
    )

    service = _build_service(vector_store)
    result = service.answer(
        "index-1",
        "Where is the chunking logic implemented?",
        top_k=1,
        include_tests=False,
    )

    assert result.answer == INSUFFICIENT_CONTEXT_ANSWER
    assert result.sources == []
