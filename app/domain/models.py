from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScannedFile:
    relative_path: str
    extension: str
    size_bytes: int
    line_count: int


@dataclass(frozen=True)
class LanguageCount:
    extension: str
    file_count: int


@dataclass
class ScanResult:
    repository_path: str
    total_files: int
    total_lines: int
    languages: list[LanguageCount] = field(default_factory=list)
    files: list[ScannedFile] = field(default_factory=list)
    ignored_directories: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkippedFile:
    file_path: str
    reason: str


@dataclass(frozen=True)
class FileContent:
    file_path: str
    extension: str
    lines: list[str]


@dataclass(frozen=True)
class ContentChunk:
    chunk_id: str
    file_path: str
    extension: str
    start_line: int
    end_line: int
    content: str


@dataclass
class ExtractionResult:
    files: list[FileContent] = field(default_factory=list)
    skipped_files: list[SkippedFile] = field(default_factory=list)


@dataclass
class ChunkingResult:
    repository_path: str
    total_files_processed: int
    total_files_skipped: int
    total_chunks: int
    chunks: list[ContentChunk] = field(default_factory=list)
    skipped_files: list[SkippedFile] = field(default_factory=list)
