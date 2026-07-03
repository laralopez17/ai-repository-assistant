from pydantic import BaseModel, Field, model_validator


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


class ChunkRequest(BaseModel):
    path: str = Field(..., min_length=1)
    max_lines_per_chunk: int = Field(default=80, gt=0)
    overlap_lines: int = Field(default=10, ge=0)

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkRequest":
        if self.overlap_lines >= self.max_lines_per_chunk:
            raise ValueError("overlap_lines must be smaller than max_lines_per_chunk")
        return self


class ChunkInfo(BaseModel):
    chunk_id: str
    file_path: str
    extension: str
    start_line: int
    end_line: int
    content: str


class SkippedFileInfo(BaseModel):
    file_path: str
    reason: str


class ChunksResponse(BaseModel):
    repository_path: str
    total_files_processed: int
    total_files_skipped: int
    total_chunks: int
    chunks: list[ChunkInfo]
    skipped_files: list[SkippedFileInfo]
