from fastapi import APIRouter, Depends, HTTPException, status

from app.core.errors import (
    AppError,
    InvalidChunkingConfigError,
    NotADirectoryError,
    PathNotFoundError,
)
from app.domain.models import ChunkingResult, ScanResult
from app.schemas.repository import (
    ChunkInfo,
    ChunkRequest,
    ChunksResponse,
    FileInfo,
    LanguageInfo,
    ScanRequest,
    ScanResponse,
    SkippedFileInfo,
)
from app.services.chunking_service import ChunkingService
from app.services.content_extractor import ContentExtractor
from app.services.repository_scanner import RepositoryScanner

router = APIRouter(prefix="/repositories", tags=["repositories"])


def get_repository_scanner() -> RepositoryScanner:
    return RepositoryScanner()


def get_content_extractor() -> ContentExtractor:
    return ContentExtractor()


def get_chunking_service() -> ChunkingService:
    return ChunkingService()


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
