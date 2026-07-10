import pytest

from app.core.errors import InvalidChunkingConfigError
from app.domain.models import FileContent
from app.services.chunking_service import ChunkingService


def _make_file(path: str, line_count: int) -> FileContent:
    return FileContent(
        file_path=path,
        extension=".txt",
        lines=[f"line-{index}" for index in range(1, line_count + 1)],
    )


def test_chunk_short_file_creates_one_chunk():
    service = ChunkingService(max_chars_per_chunk=12000)
    chunks = service.chunk_files([_make_file("short.txt", 20)], 80, 10)

    assert len(chunks) == 1
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 20
    assert chunks[0].chunk_id == "short.txt::chunk-000"
    assert chunks[0].content.count("\n") == 19


def test_chunk_long_file_creates_multiple_chunks():
    service = ChunkingService(max_chars_per_chunk=12000)
    chunks = service.chunk_files([_make_file("long.txt", 150)], 80, 10)

    assert len(chunks) == 2
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 80
    assert chunks[1].start_line == 71
    assert chunks[1].end_line == 150


def test_chunk_overlap_is_applied_between_chunks():
    service = ChunkingService(max_chars_per_chunk=12000)
    chunks = service.chunk_files([_make_file("overlap.txt", 100)], 30, 5)

    assert chunks[0].end_line == 30
    assert chunks[1].start_line == 26
    assert chunks[1].end_line == 55

    first_tail = chunks[0].content.splitlines()[-5:]
    second_head = chunks[1].content.splitlines()[:5]
    assert first_tail == second_head


def test_chunk_normalizes_windows_path_in_chunk_id():
    service = ChunkingService(max_chars_per_chunk=12000)
    chunks = service.chunk_files(
        [_make_file("app\\services\\repository_scanner.py", 5)],
        80,
        10,
    )

    assert chunks[0].chunk_id == "app/services/repository_scanner.py::chunk-000"
    assert chunks[0].file_path == "app/services/repository_scanner.py"


def test_chunk_raises_for_invalid_overlap():
    service = ChunkingService(max_chars_per_chunk=12000)

    with pytest.raises(InvalidChunkingConfigError):
        service.chunk_files([_make_file("file.txt", 10)], 80, 80)

    with pytest.raises(InvalidChunkingConfigError):
        service.chunk_files([_make_file("file.txt", 10)], 80, 100)


def test_chunk_splits_very_long_line_by_chars():
    long_line = "a" * 25000
    file_content = FileContent(
        file_path="minified.js",
        extension=".js",
        lines=[long_line],
    )
    service = ChunkingService(max_chars_per_chunk=10000)

    chunks = service.chunk_files([file_content], 80, 10)

    assert len(chunks) == 3
    assert [chunk.chunk_id for chunk in chunks] == [
        "minified.js::chunk-000",
        "minified.js::chunk-001",
        "minified.js::chunk-002",
    ]
    assert all(len(chunk.content) <= 10000 for chunk in chunks)
    assert "".join(chunk.content for chunk in chunks) == long_line
    assert all(chunk.start_line == 1 and chunk.end_line == 1 for chunk in chunks)


def test_chunk_every_result_respects_max_chars_per_chunk():
    lines = ["x" * 4000 for _ in range(5)]
    file_content = FileContent(
        file_path="wide.txt",
        extension=".txt",
        lines=lines,
    )
    service = ChunkingService(max_chars_per_chunk=5000)

    chunks = service.chunk_files([file_content], 80, 10)

    assert len(chunks) > 1
    assert all(len(chunk.content) <= 5000 for chunk in chunks)
    assert [chunk.chunk_id for chunk in chunks] == [
        f"wide.txt::chunk-{index:03d}" for index in range(len(chunks))
    ]


def test_chunk_raises_for_invalid_max_chars_per_chunk():
    with pytest.raises(InvalidChunkingConfigError):
        ChunkingService(max_chars_per_chunk=0)
