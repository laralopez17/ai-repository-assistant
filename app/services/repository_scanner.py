import os
from collections import Counter
from pathlib import Path

from app.core.config import DEFAULT_IGNORED_DIRECTORIES
from app.core.errors import NotADirectoryError, PathNotFoundError
from app.domain.models import LanguageCount, ScanResult, ScannedFile
from app.utils.file_filters import (
    count_lines,
    is_ignored_directory,
    normalize_extension,
    should_skip_file,
)


class RepositoryScanner:
    def __init__(self, ignored_directories: frozenset[str] | None = None) -> None:
        self._ignored_directories = ignored_directories or DEFAULT_IGNORED_DIRECTORIES

    def scan(self, path: str | Path) -> ScanResult:
        repository_path = Path(path).expanduser().resolve()

        if not repository_path.exists():
            raise PathNotFoundError(f"Path does not exist: {path}")

        if not repository_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")

        files: list[ScannedFile] = []
        ignored_directories: set[str] = set()
        extension_counts: Counter[str] = Counter()

        for current_dir, dir_names, file_names in self._walk(repository_path):
            relative_dir = current_dir.relative_to(repository_path)
            self._filter_directories(dir_names, relative_dir, ignored_directories)

            for file_name in file_names:
                file_path = current_dir / file_name
                relative_path = file_path.relative_to(repository_path).as_posix()

                if should_skip_file(file_path):
                    continue

                extension = normalize_extension(file_path)
                line_count = count_lines(file_path)
                size_bytes = file_path.stat().st_size

                files.append(
                    ScannedFile(
                        relative_path=relative_path,
                        extension=extension,
                        size_bytes=size_bytes,
                        line_count=line_count,
                    )
                )
                extension_counts[extension] += 1

        languages = [
            LanguageCount(extension=extension, file_count=count)
            for extension, count in sorted(extension_counts.items())
        ]

        return ScanResult(
            repository_path=str(repository_path),
            total_files=len(files),
            total_lines=sum(file.line_count for file in files),
            languages=languages,
            files=sorted(files, key=lambda file: file.relative_path),
            ignored_directories=sorted(ignored_directories),
        )

    def _walk(self, root: Path):
        for current_dir, dir_names, file_names in os.walk(root):
            yield Path(current_dir), dir_names, file_names

    def _filter_directories(
        self,
        dir_names: list[str],
        relative_dir: Path,
        ignored_directories: set[str],
    ) -> None:
        skipped: list[str] = []
        for name in dir_names:
            if is_ignored_directory(name, self._ignored_directories):
                if relative_dir == Path("."):
                    ignored_directories.add(name)
                else:
                    ignored_directories.add((relative_dir / name).as_posix())
                skipped.append(name)
        for name in skipped:
            dir_names.remove(name)
