from fastapi import APIRouter, Depends, HTTPException, status

from app.core.errors import AppError, NotADirectoryError, PathNotFoundError
from app.domain.models import ScanResult
from app.schemas.repository import (
    FileInfo,
    LanguageInfo,
    ScanRequest,
    ScanResponse,
)
from app.services.repository_scanner import RepositoryScanner

router = APIRouter(prefix="/repositories", tags=["repositories"])


def get_repository_scanner() -> RepositoryScanner:
    return RepositoryScanner()


def _to_response(result: ScanResult) -> ScanResponse:
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


@router.post("/scan", response_model=ScanResponse)
def scan_repository(
    request: ScanRequest,
    scanner: RepositoryScanner = Depends(get_repository_scanner),
) -> ScanResponse:
    try:
        result = scanner.scan(request.path)
    except PathNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.message,
        ) from error
    except NotADirectoryError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.message,
        ) from error
    except AppError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.message,
        ) from error

    return _to_response(result)
