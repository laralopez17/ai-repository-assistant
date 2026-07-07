import json
import sqlite3
from pathlib import Path

from app.core.database import connect
from app.core.errors import DatabaseError, IndexNotFoundError
from app.domain.models import EmbeddedChunk, RepositoryIndex, SearchResult
from app.utils.similarity import cosine_similarity
from app.utils.source_type import SOURCE_TYPE_TEST


class SQLiteIndexStore:
    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)

    def store_index(
        self,
        repository_index: RepositoryIndex,
        embedded_chunks: list[EmbeddedChunk],
    ) -> None:
        try:
            with connect(self._db_path) as connection:
                connection.execute(
                    """
                    INSERT INTO indexes (
                        index_id,
                        repository_path,
                        embedding_model,
                        total_chunks_indexed,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        repository_index.index_id,
                        repository_index.repository_path,
                        repository_index.embedding_model,
                        repository_index.total_chunks_indexed,
                        repository_index.created_at,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO chunks (
                        index_id,
                        chunk_id,
                        file_path,
                        extension,
                        start_line,
                        end_line,
                        content,
                        source_type,
                        embedding_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            repository_index.index_id,
                            chunk.chunk_id,
                            chunk.file_path,
                            chunk.extension,
                            chunk.start_line,
                            chunk.end_line,
                            chunk.content,
                            chunk.source_type,
                            json.dumps(chunk.embedding),
                        )
                        for chunk in embedded_chunks
                    ],
                )
                connection.commit()
        except sqlite3.Error as error:
            raise DatabaseError(
                f"Failed to store repository index: {error}"
            ) from error

    def get_index(self, index_id: str) -> RepositoryIndex:
        try:
            with connect(self._db_path) as connection:
                row = connection.execute(
                    """
                    SELECT
                        index_id,
                        repository_path,
                        embedding_model,
                        total_chunks_indexed,
                        created_at
                    FROM indexes
                    WHERE index_id = ?
                    """,
                    (index_id,),
                ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseError(
                f"Failed to load repository index: {error}"
            ) from error

        if row is None:
            raise IndexNotFoundError(f"Index not found: {index_id}")

        return self._row_to_repository_index(row)

    def list_indexes(self) -> list[RepositoryIndex]:
        try:
            with connect(self._db_path) as connection:
                rows = connection.execute(
                    """
                    SELECT
                        index_id,
                        repository_path,
                        embedding_model,
                        total_chunks_indexed,
                        created_at
                    FROM indexes
                    ORDER BY created_at DESC
                    """
                ).fetchall()
        except sqlite3.Error as error:
            raise DatabaseError(
                f"Failed to list repository indexes: {error}"
            ) from error

        return [self._row_to_repository_index(row) for row in rows]

    def delete_index(self, index_id: str) -> None:
        try:
            with connect(self._db_path) as connection:
                cursor = connection.execute(
                    "DELETE FROM indexes WHERE index_id = ?",
                    (index_id,),
                )
                connection.commit()
        except sqlite3.Error as error:
            raise DatabaseError(
                f"Failed to delete repository index: {error}"
            ) from error

        if cursor.rowcount == 0:
            raise IndexNotFoundError(f"Index not found: {index_id}")

    def search(
        self,
        index_id: str,
        query_embedding: list[float],
        top_k: int,
        include_tests: bool = True,
    ) -> list[SearchResult]:
        try:
            with connect(self._db_path) as connection:
                index_row = connection.execute(
                    "SELECT index_id FROM indexes WHERE index_id = ?",
                    (index_id,),
                ).fetchone()
                if index_row is None:
                    raise IndexNotFoundError(f"Index not found: {index_id}")

                chunk_rows = connection.execute(
                    """
                    SELECT
                        chunk_id,
                        file_path,
                        start_line,
                        end_line,
                        content,
                        source_type,
                        embedding_json
                    FROM chunks
                    WHERE index_id = ?
                    """,
                    (index_id,),
                ).fetchall()
        except IndexNotFoundError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError(
                f"Failed to search repository index: {error}"
            ) from error

        scored_results: list[SearchResult] = []
        for row in chunk_rows:
            if not include_tests and row["source_type"] == SOURCE_TYPE_TEST:
                continue

            embedding = json.loads(row["embedding_json"])
            score = cosine_similarity(query_embedding, embedding)
            scored_results.append(
                SearchResult(
                    chunk_id=row["chunk_id"],
                    file_path=row["file_path"],
                    start_line=row["start_line"],
                    end_line=row["end_line"],
                    score=score,
                    content=row["content"],
                    source_type=row["source_type"],
                )
            )

        scored_results.sort(key=lambda result: result.score, reverse=True)
        return scored_results[:top_k]

    def _row_to_repository_index(self, row: sqlite3.Row) -> RepositoryIndex:
        return RepositoryIndex(
            index_id=row["index_id"],
            repository_path=row["repository_path"],
            total_chunks_indexed=row["total_chunks_indexed"],
            embedding_model=row["embedding_model"],
            created_at=row["created_at"],
        )
