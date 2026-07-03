from pathlib import Path

import pytest

from app.domain.models import ScannedFile
from app.services.content_extractor import ContentExtractor


def test_extract_reads_text_file(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "main.py"
    file_path.write_text("line one\nline two\n", encoding="utf-8")

    extractor = ContentExtractor()
    result = extractor.extract(
        str(repo),
        [
            ScannedFile(
                relative_path="main.py",
                extension=".py",
                size_bytes=file_path.stat().st_size,
                line_count=2,
            )
        ],
    )

    assert len(result.files) == 1
    assert result.files[0].lines == ["line one", "line two"]
    assert result.skipped_files == []


def test_extract_skips_invalid_utf8_file(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "invalid.txt"
    file_path.write_bytes(b"\xff\xfe\xfd")

    extractor = ContentExtractor()
    result = extractor.extract(
        str(repo),
        [
            ScannedFile(
                relative_path="invalid.txt",
                extension=".txt",
                size_bytes=file_path.stat().st_size,
                line_count=0,
            )
        ],
    )

    assert result.files == []
    assert len(result.skipped_files) == 1
    assert result.skipped_files[0].file_path == "invalid.txt"
    assert result.skipped_files[0].reason == "cannot decode as utf-8"


def test_extract_skips_unreadable_file(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    extractor = ContentExtractor()
    result = extractor.extract(
        str(repo),
        [
            ScannedFile(
                relative_path="missing.txt",
                extension=".txt",
                size_bytes=0,
                line_count=0,
            )
        ],
    )

    assert result.files == []
    assert len(result.skipped_files) == 1
    assert result.skipped_files[0].file_path == "missing.txt"
    assert result.skipped_files[0].reason == "cannot read file"
