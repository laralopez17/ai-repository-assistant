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
