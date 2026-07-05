import pytest

from app.utils.source_type import detect_source_type


@pytest.mark.parametrize(
    ("file_path", "extension", "expected"),
    [
        ("app/services/chunking_service.py", ".py", "source"),
        ("src/main.py", ".py", "source"),
        ("lib/utils/helpers.py", ".py", "source"),
        ("tests/test_chunking_service.py", ".py", "test"),
        ("test_helpers.py", ".py", "test"),
        ("README.md", ".md", "docs"),
        ("docs/guide.md", ".md", "docs"),
        ("pyproject.toml", ".toml", "config"),
        ("requirements.txt", ".txt", "config"),
        ("data/output.csv", ".csv", "other"),
    ],
)
def test_detect_source_type(file_path: str, extension: str, expected: str):
    assert detect_source_type(file_path, extension) == expected
