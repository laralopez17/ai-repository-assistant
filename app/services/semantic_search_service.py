from app.domain.models import SearchResult
from app.services.embedding_provider import EmbeddingProvider
from app.services.vector_store import VectorStore
from app.utils.source_type import SOURCE_TYPE_TEST


class SemanticSearchService:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    def search(
        self,
        index_id: str,
        query: str,
        top_k: int,
        include_tests: bool = True,
    ) -> list[SearchResult]:
        query_embedding = self._embedding_provider.embed_text(query)
        results = self._vector_store.search(index_id, query_embedding)

        if not include_tests:
            results = [
                result for result in results if result.source_type != SOURCE_TYPE_TEST
            ]

        return results[:top_k]
