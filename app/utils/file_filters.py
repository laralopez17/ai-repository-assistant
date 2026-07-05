from pathlib import Path
import fnmatch

from app.core.config import (
    BINARY_SAMPLE_SIZE,
    DEFAULT_IGNORED_FILE_GLOBS,
    DEFAULT_IGNORED_FILES,
    MAX_FILE_SIZE_BYTES,
)


def is_ignored_directory(name: str, ignored_names: frozenset[str]) -> bool:
    return name in ignored_names


def is_ignored_file(
    path: Path,
    ignored_names: frozenset[str] | None = None,
    ignored_globs: tuple[str, ...] | None = None,
) -> bool:
    file_names = ignored_names if ignored_names is not None else DEFAULT_IGNORED_FILES
    file_globs = ignored_globs if ignored_globs is not None else DEFAULT_IGNORED_FILE_GLOBS
    file_name = path.name

    if file_name in file_names:
        return True

    return any(fnmatch.fnmatch(file_name, pattern) for pattern in file_globs)


def is_binary_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(BINARY_SAMPLE_SIZE)
    except OSError:
        return True
    return b"\x00" in chunk


def is_too_large(path: Path, max_size_bytes: int = MAX_FILE_SIZE_BYTES) -> bool:
    try:
        return path.stat().st_size > max_size_bytes
    except OSError:
        return True


def should_skip_file(path: Path) -> bool:
    return is_binary_file(path) or is_too_large(path)


def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="strict") as handle:
            return sum(1 for _ in handle)
    except (OSError, UnicodeDecodeError):
        return 0


def normalize_extension(path: Path) -> str:
    suffix = path.suffix.lower()
    return suffix if suffix else "(no extension)"
