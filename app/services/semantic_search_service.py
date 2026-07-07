from app.domain.models import SearchResult
from app.services.embedding_provider import EmbeddingProvider
from app.services.index_store import IndexStore


class SemanticSearchService:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        index_store: IndexStore,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._index_store = index_store

    def search(
        self,
        index_id: str,
        query: str,
        top_k: int,
        include_tests: bool = True,
    ) -> list[SearchResult]:
        query_embedding = self._embedding_provider.embed_text(query)
        return self._index_store.search(
            index_id,
            query_embedding,
            top_k,
            include_tests,
        )
