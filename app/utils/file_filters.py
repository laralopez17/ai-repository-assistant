from pathlib import Path

from app.core.config import BINARY_SAMPLE_SIZE, MAX_FILE_SIZE_BYTES


def is_ignored_directory(name: str, ignored_names: frozenset[str]) -> bool:
    return name in ignored_names


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
