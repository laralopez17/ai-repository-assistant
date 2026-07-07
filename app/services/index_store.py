from typing import Protocol

from app.domain.models import EmbeddedChunk, RepositoryIndex, SearchResult


class IndexStore(Protocol):
    def store_index(
        self,
        repository_index: RepositoryIndex,
        embedded_chunks: list[EmbeddedChunk],
    ) -> None:
        ...

    def get_index(self, index_id: str) -> RepositoryIndex:
        ...

    def list_indexes(self) -> list[RepositoryIndex]:
        ...

    def delete_index(self, index_id: str) -> None:
        ...

    def search(
        self,
        index_id: str,
        query_embedding: list[float],
        top_k: int,
        include_tests: bool = True,
    ) -> list[SearchResult]:
        ...
