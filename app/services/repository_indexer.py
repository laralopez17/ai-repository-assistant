import uuid

from app.core import config
from app.core.errors import ChunkLimitExceededError
from app.domain.models import ContentChunk, EmbeddedChunk, RepositoryIndex
from app.services.chunking_service import ChunkingService
from app.services.content_extractor import ContentExtractor
from app.services.embedding_provider import EmbeddingProvider
from app.services.repository_scanner import RepositoryScanner
from app.services.vector_store import VectorStore


class RepositoryIndexer:
    def __init__(
        self,
        scanner: RepositoryScanner,
        content_extractor: ContentExtractor,
        chunking_service: ChunkingService,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        max_chunks_to_embed: int | None = None,
    ) -> None:
        self._scanner = scanner
        self._content_extractor = content_extractor
        self._chunking_service = chunking_service
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._max_chunks_to_embed = (
            max_chunks_to_embed
            if max_chunks_to_embed is not None
            else config.MAX_CHUNKS_TO_EMBED
        )

    def index_repository(
        self,
        path: str,
        max_lines_per_chunk: int,
        overlap_lines: int,
    ) -> RepositoryIndex:
        scan_result = self._scanner.scan(path)
        extraction_result = self._content_extractor.extract(
            scan_result.repository_path,
            scan_result.files,
        )
        chunks = self._chunking_service.chunk_files(
            extraction_result.files,
            max_lines_per_chunk,
            overlap_lines,
        )

        if not chunks:
            raise ValueError("No chunks available to index for the given repository")

        if len(chunks) > self._max_chunks_to_embed:
            raise ChunkLimitExceededError(
                f"Repository produced {len(chunks)} chunks, exceeding the limit of "
                f"{self._max_chunks_to_embed}. Increase MAX_CHUNKS_TO_EMBED or "
                "reduce repository size."
            )

        embeddings = self._embedding_provider.embed_texts(
            [chunk.content for chunk in chunks]
        )
        embedded_chunks = [
            self._to_embedded_chunk(chunk, embedding)
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]

        index_id = str(uuid.uuid4())
        repository_index = RepositoryIndex(
            index_id=index_id,
            repository_path=scan_result.repository_path,
            total_chunks_indexed=len(embedded_chunks),
            embedding_model=self._embedding_provider.model_name,
        )
        self._vector_store.store_index(repository_index, embedded_chunks)
        return repository_index

    def _to_embedded_chunk(
        self,
        chunk: ContentChunk,
        embedding: list[float],
    ) -> EmbeddedChunk:
        return EmbeddedChunk(
            chunk_id=chunk.chunk_id,
            file_path=chunk.file_path,
            extension=chunk.extension,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            content=chunk.content,
            source_type=chunk.source_type,
            embedding=embedding,
        )
