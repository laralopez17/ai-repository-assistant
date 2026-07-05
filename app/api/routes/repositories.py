from fastapi import APIRouter, Depends, HTTPException, status

from app.core.errors import (
    AppError,
    ChunkLimitExceededError,
    EmbeddingProviderError,
    IndexNotFoundError,
    InvalidChunkingConfigError,
    MissingApiKeyError,
    NotADirectoryError,
    PathNotFoundError,
    UnsupportedProviderError,
)
from app.domain.models import ChunkingResult, ScanResult
from app.schemas.repository import (
    ChunkInfo,
    ChunkRequest,
    ChunksResponse,
    FileInfo,
    IndexRequest,
    IndexResponse,
    LanguageInfo,
    ScanRequest,
    ScanResponse,
    SearchRequest,
    SearchResponse,
    SearchResultInfo,
    SkippedFileInfo,
)
from app.services.chunking_service import ChunkingService
from app.services.content_extractor import ContentExtractor
from app.services.embedding_factory import get_embedding_provider
from app.services.embedding_provider import EmbeddingProvider
from app.services.repository_indexer import RepositoryIndexer
from app.services.repository_scanner import RepositoryScanner
from app.services.semantic_search_service import SemanticSearchService
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/repositories", tags=["repositories"])

_vector_store = VectorStore()


def get_repository_scanner() -> RepositoryScanner:
    return RepositoryScanner()


def get_content_extractor() -> ContentExtractor:
    return ContentExtractor()


def get_chunking_service() -> ChunkingService:
    return ChunkingService()


def get_vector_store() -> VectorStore:
    return _vector_store


def get_repository_indexer(
    scanner: RepositoryScanner = Depends(get_repository_scanner),
    content_extractor: ContentExtractor = Depends(get_content_extractor),
    chunking_service: ChunkingService = Depends(get_chunking_service),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: VectorStore = Depends(get_vector_store),
) -> RepositoryIndexer:
    return RepositoryIndexer(
        scanner=scanner,
        content_extractor=content_extractor,
        chunking_service=chunking_service,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )


def get_semantic_search_service(
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: VectorStore = Depends(get_vector_store),
) -> SemanticSearchService:
    return SemanticSearchService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )


def _to_scan_response(result: ScanResult) -> ScanResponse:
    return ScanResponse(
        repository_path=result.repository_path,
        total_files=result.total_files,
        total_lines=result.total_lines,
        languages=[
            LanguageInfo(extension=language.extension, file_count=language.file_count)
            for language in result.languages
        ],
        files=[
            FileInfo(
                relative_path=file.relative_path,
                extension=file.extension,
                size_bytes=file.size_bytes,
                line_count=file.line_count,
            )
            for file in result.files
        ],
        ignored_directories=result.ignored_directories,
        ignored_files=result.ignored_files,
    )


def _to_chunks_response(result: ChunkingResult) -> ChunksResponse:
    return ChunksResponse(
        repository_path=result.repository_path,
        total_files_processed=result.total_files_processed,
        total_files_skipped=result.total_files_skipped,
        total_chunks=result.total_chunks,
        chunks=[
            ChunkInfo(
                chunk_id=chunk.chunk_id,
                file_path=chunk.file_path,
                extension=chunk.extension,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                content=chunk.content,
                source_type=chunk.source_type,
            )
            for chunk in result.chunks
        ],
        skipped_files=[
            SkippedFileInfo(file_path=skipped.file_path, reason=skipped.reason)
            for skipped in result.skipped_files
        ],
    )


def _map_repository_errors(error: AppError) -> HTTPException:
    if isinstance(error, PathNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.message,
        )
    if isinstance(error, IndexNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.message,
        )
    if isinstance(error, NotADirectoryError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.message,
        )
    if isinstance(error, InvalidChunkingConfigError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.message,
        )
    if isinstance(error, MissingApiKeyError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error.message,
        )
    if isinstance(error, EmbeddingProviderError):
        return HTTPException(
            status_code=error.status_code or status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error.message,
        )
    if isinstance(error, ChunkLimitExceededError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.message,
        )
    if isinstance(error, UnsupportedProviderError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error.message,
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=error.message,
    )


@router.post("/scan", response_model=ScanResponse)
def scan_repository(
    request: ScanRequest,
    scanner: RepositoryScanner = Depends(get_repository_scanner),
) -> ScanResponse:
    try:
        result = scanner.scan(request.path)
    except AppError as error:
        raise _map_repository_errors(error) from error

    return _to_scan_response(result)


@router.post("/chunks", response_model=ChunksResponse)
def chunk_repository(
    request: ChunkRequest,
    scanner: RepositoryScanner = Depends(get_repository_scanner),
    content_extractor: ContentExtractor = Depends(get_content_extractor),
    chunking_service: ChunkingService = Depends(get_chunking_service),
) -> ChunksResponse:
    try:
        scan_result = scanner.scan(request.path)
        extraction_result = content_extractor.extract(
            scan_result.repository_path,
            scan_result.files,
        )
        chunks = chunking_service.chunk_files(
            extraction_result.files,
            request.max_lines_per_chunk,
            request.overlap_lines,
        )
    except AppError as error:
        raise _map_repository_errors(error) from error

    result = ChunkingResult(
        repository_path=scan_result.repository_path,
        total_files_processed=len(extraction_result.files),
        total_files_skipped=len(extraction_result.skipped_files),
        total_chunks=len(chunks),
        chunks=chunks,
        skipped_files=extraction_result.skipped_files,
    )

    return _to_chunks_response(result)


@router.post("/index", response_model=IndexResponse)
def index_repository(
    request: IndexRequest,
    repository_indexer: RepositoryIndexer = Depends(get_repository_indexer),
) -> IndexResponse:
    try:
        repository_index = repository_indexer.index_repository(
            request.path,
            request.max_lines_per_chunk,
            request.overlap_lines,
        )
    except AppError as error:
        raise _map_repository_errors(error) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return IndexResponse(
        index_id=repository_index.index_id,
        repository_path=repository_index.repository_path,
        total_chunks_indexed=repository_index.total_chunks_indexed,
        embedding_model=repository_index.embedding_model,
    )


@router.post("/search", response_model=SearchResponse)
def search_repository(
    request: SearchRequest,
    semantic_search_service: SemanticSearchService = Depends(get_semantic_search_service),
) -> SearchResponse:
    try:
        results = semantic_search_service.search(
            request.index_id,
            request.query,
            request.top_k,
            request.include_tests,
        )
    except AppError as error:
        raise _map_repository_errors(error) from error

    return SearchResponse(
        index_id=request.index_id,
        query=request.query,
        total_results=len(results),
        results=[
            SearchResultInfo(
                chunk_id=result.chunk_id,
                file_path=result.file_path,
                start_line=result.start_line,
                end_line=result.end_line,
                score=round(result.score, 4),
                content=result.content,
                source_type=result.source_type,
            )
            for result in results
        ],
    )
