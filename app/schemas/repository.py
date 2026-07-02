from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    path: str = Field(..., min_length=1)


class FileInfo(BaseModel):
    relative_path: str
    extension: str
    size_bytes: int
    line_count: int


class LanguageInfo(BaseModel):
    extension: str
    file_count: int


class ScanResponse(BaseModel):
    repository_path: str
    total_files: int
    total_lines: int
    languages: list[LanguageInfo]
    files: list[FileInfo]
    ignored_directories: list[str]
