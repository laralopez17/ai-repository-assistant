import numpy as np

from app.core.errors import IndexNotFoundError
from app.domain.models import EmbeddedChunk, RepositoryIndex, SearchResult


def cosine_similarity(left: list[float], right: list[float]) -> float:
    left_vector = np.asarray(left, dtype=float)
    right_vector = np.asarray(right, dtype=float)
    left_norm = np.linalg.norm(left_vector)
    right_norm = np.linalg.norm(right_vector)

    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    return float(np.dot(left_vector, right_vector) / (left_norm * right_norm))


class VectorStore:
    def __init__(self) -> None:
        self._indexes: dict[str, RepositoryIndex] = {}
        self._embedded_chunks: dict[str, list[EmbeddedChunk]] = {}

    def store_index(
        self,
        repository_index: RepositoryIndex,
        embedded_chunks: list[EmbeddedChunk],
    ) -> None:
        self._indexes[repository_index.index_id] = repository_index
        self._embedded_chunks[repository_index.index_id] = embedded_chunks

    def has_index(self, index_id: str) -> bool:
        return index_id in self._indexes and index_id in self._embedded_chunks

    def get_index(self, index_id: str) -> RepositoryIndex:
        if index_id not in self._indexes:
            raise IndexNotFoundError(f"Index not found: {index_id}")
        return self._indexes[index_id]

    def search(
        self,
        index_id: str,
        query_embedding: list[float],
    ) -> list[SearchResult]:
        if not self.has_index(index_id):
            raise IndexNotFoundError(f"Index not found: {index_id}")

        scored_results: list[SearchResult] = []
        for chunk in self._embedded_chunks[index_id]:
            score = cosine_similarity(query_embedding, chunk.embedding)
            scored_results.append(
                SearchResult(
                    chunk_id=chunk.chunk_id,
                    file_path=chunk.file_path,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    score=score,
                    content=chunk.content,
                    source_type=chunk.source_type,
                )
            )

        scored_results.sort(key=lambda result: result.score, reverse=True)
        return scored_results
