from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import MAX_CHARS_PER_CHUNK, SQLITE_DB_PATH
from app.core.database import init_database
from app.core.errors import (
    AppError,
    ChunkLimitExceededError,
    DatabaseError,
    EmbeddingProviderError,
    GitCloneError,
    GitCloneTimeoutError,
    GitHubRepositoryNotFoundError,
    GitNotInstalledError,
    IndexNotFoundError,
    InvalidChunkingConfigError,
    InvalidGitHubUrlError,
    LLMProviderError,
    MissingApiKeyError,
    NotADirectoryError,
    PathNotFoundError,
    UnsupportedProviderError,
)
from app.domain.models import ChunkingResult, RAGAnswerResult, ScanResult
from app.schemas.repository import (
    AskRequest,
    AskResponse,
    AskSourceInfo,
    ChunkInfo,
    ChunkRequest,
    ChunksResponse,
    DeleteIndexResponse,
    FileInfo,
    GitHubRepositoryIndexRequest,
    GitHubRepositoryIndexResponse,
    IndexListResponse,
    IndexMetadata,
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
from app.services.github_repository_ingestor import GitHubRepositoryIngestor
from app.services.index_store import IndexStore
from app.services.llm_provider_factory import get_llm_provider
from app.services.llm_provider import LLMProvider
from app.services.rag_answer_service import RAGAnswerService
from app.services.repository_indexer import RepositoryIndexer
from app.services.repository_scanner import RepositoryScanner
from app.services.semantic_search_service import SemanticSearchService
from app.services.sqlite_index_store import SQLiteIndexStore

router = APIRouter(prefix="/repositories", tags=["repositories"])

_index_store = SQLiteIndexStore(SQLITE_DB_PATH)
init_database(SQLITE_DB_PATH)


def get_repository_scanner() -> RepositoryScanner:
    return RepositoryScanner()


def get_content_extractor() -> ContentExtractor:
    return ContentExtractor()


def get_chunking_service() -> ChunkingService:
    return ChunkingService(max_chars_per_chunk=MAX_CHARS_PER_CHUNK)


def get_index_store() -> IndexStore:
    return _index_store


def get_repository_indexer(
    scanner: RepositoryScanner = Depends(get_repository_scanner),
    content_extractor: ContentExtractor = Depends(get_content_extractor),
    chunking_service: ChunkingService = Depends(get_chunking_service),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    index_store: IndexStore = Depends(get_index_store),
) -> RepositoryIndexer:
    return RepositoryIndexer(
        scanner=scanner,
        content_extractor=content_extractor,
        chunking_service=chunking_service,
        embedding_provider=embedding_provider,
        index_store=index_store,
    )


def get_github_repository_ingestor(
    repository_indexer: RepositoryIndexer = Depends(get_repository_indexer),
) -> GitHubRepositoryIngestor:
    return GitHubRepositoryIngestor(repository_indexer)


def get_semantic_search_service(
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    index_store: IndexStore = Depends(get_index_store),
) -> SemanticSearchService:
    return SemanticSearchService(
        embedding_provider=embedding_provider,
        index_store=index_store,
    )


def get_rag_answer_service(
    semantic_search_service: SemanticSearchService = Depends(get_semantic_search_service),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> RAGAnswerService:
    return RAGAnswerService(
        semantic_search_service=semantic_search_service,
        llm_provider=llm_provider,
    )


def _to_index_metadata(repository_index) -> IndexMetadata:
    return IndexMetadata(
        index_id=repository_index.index_id,
        repository_path=repository_index.repository_path,
        embedding_model=repository_index.embedding_model,
        total_chunks_indexed=repository_index.total_chunks_indexed,
        created_at=repository_index.created_at,
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
    if isinstance(error, LLMProviderError):
        return HTTPException(
            status_code=error.status_code or status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error.message,
        )
    if isinstance(error, ChunkLimitExceededError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.message,
        )
    if isinstance(error, DatabaseError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error.message,
        )
    if isinstance(error, UnsupportedProviderError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error.message,
        )
    if isinstance(error, InvalidGitHubUrlError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.message,
        )
    if isinstance(error, GitHubRepositoryNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.message,
        )
    if isinstance(error, GitCloneTimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=error.message,
        )
    if isinstance(error, (GitCloneError, GitNotInstalledError)):
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


@router.post("/index-github", response_model=GitHubRepositoryIndexResponse)
def index_github_repository(
    request: GitHubRepositoryIndexRequest,
    github_ingestor: GitHubRepositoryIngestor = Depends(get_github_repository_ingestor),
) -> GitHubRepositoryIndexResponse:
    try:
        result = github_ingestor.index_github_repository(request.url)
    except AppError as error:
        raise _map_repository_errors(error) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return GitHubRepositoryIndexResponse(
        index_id=result.index_id,
        repository_path=result.repository_path,
        total_chunks_indexed=result.total_chunks_indexed,
        embedding_model=result.embedding_model,
        source=result.source,
        github_url=result.github_url,
    )


@router.get("/indexes", response_model=IndexListResponse)
def list_repository_indexes(
    index_store: IndexStore = Depends(get_index_store),
) -> IndexListResponse:
    try:
        indexes = index_store.list_indexes()
    except AppError as error:
        raise _map_repository_errors(error) from error

    return IndexListResponse(
        indexes=[_to_index_metadata(repository_index) for repository_index in indexes]
    )


@router.get("/indexes/{index_id}", response_model=IndexMetadata)
def get_repository_index(
    index_id: str,
    index_store: IndexStore = Depends(get_index_store),
) -> IndexMetadata:
    try:
        repository_index = index_store.get_index(index_id)
    except AppError as error:
        raise _map_repository_errors(error) from error

    return _to_index_metadata(repository_index)


@router.delete("/indexes/{index_id}", response_model=DeleteIndexResponse)
def delete_repository_index(
    index_id: str,
    index_store: IndexStore = Depends(get_index_store),
) -> DeleteIndexResponse:
    try:
        index_store.delete_index(index_id)
    except AppError as error:
        raise _map_repository_errors(error) from error

    return DeleteIndexResponse(deleted=True, index_id=index_id)


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


def _to_ask_response(result: RAGAnswerResult) -> AskResponse:
    return AskResponse(
        index_id=result.index_id,
        question=result.question,
        answer=result.answer,
        sources=[
            AskSourceInfo(
                chunk_id=source.chunk_id,
                file_path=source.file_path,
                start_line=source.start_line,
                end_line=source.end_line,
                score=round(source.score, 4),
                source_type=source.source_type,
            )
            for source in result.sources
        ],
    )


@router.post("/ask", response_model=AskResponse)
def ask_repository(
    request: AskRequest,
    rag_answer_service: RAGAnswerService = Depends(get_rag_answer_service),
) -> AskResponse:
    try:
        result = rag_answer_service.answer(
            request.index_id,
            request.question,
            request.top_k,
            request.include_tests,
        )
    except AppError as error:
        raise _map_repository_errors(error) from error

    return _to_ask_response(result)
