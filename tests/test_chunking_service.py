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
    service = ChunkingService()
    chunks = service.chunk_files([_make_file("short.txt", 20)], 80, 10)

    assert len(chunks) == 1
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 20
    assert chunks[0].chunk_id == "short.txt::chunk-000"
    assert chunks[0].content.count("\n") == 19


def test_chunk_long_file_creates_multiple_chunks():
    service = ChunkingService()
    chunks = service.chunk_files([_make_file("long.txt", 150)], 80, 10)

    assert len(chunks) == 2
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 80
    assert chunks[1].start_line == 71
    assert chunks[1].end_line == 150


def test_chunk_overlap_is_applied_between_chunks():
    service = ChunkingService()
    chunks = service.chunk_files([_make_file("overlap.txt", 100)], 30, 5)

    assert chunks[0].end_line == 30
    assert chunks[1].start_line == 26
    assert chunks[1].end_line == 55

    first_tail = chunks[0].content.splitlines()[-5:]
    second_head = chunks[1].content.splitlines()[:5]
    assert first_tail == second_head


def test_chunk_normalizes_windows_path_in_chunk_id():
    service = ChunkingService()
    chunks = service.chunk_files(
        [_make_file("app\\services\\repository_scanner.py", 5)],
        80,
        10,
    )

    assert chunks[0].chunk_id == "app/services/repository_scanner.py::chunk-000"
    assert chunks[0].file_path == "app/services/repository_scanner.py"


def test_chunk_raises_for_invalid_overlap():
    service = ChunkingService()

    with pytest.raises(InvalidChunkingConfigError):
        service.chunk_files([_make_file("file.txt", 10)], 80, 80)

    with pytest.raises(InvalidChunkingConfigError):
        service.chunk_files([_make_file("file.txt", 10)], 80, 100)
