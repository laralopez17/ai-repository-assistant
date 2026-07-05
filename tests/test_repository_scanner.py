from pathlib import Path

import pytest

from app.core.errors import NotADirectoryError, PathNotFoundError
from app.services.repository_scanner import RepositoryScanner


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample-repo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello')\nprint('world')\n", encoding="utf-8")
    (repo / "README.md").write_text("# Sample\n", encoding="utf-8")

    node_modules = repo / "node_modules" / "pkg"
    node_modules.mkdir(parents=True)
    (node_modules / "index.js").write_text("module.exports = {};\n", encoding="utf-8")

    git_dir = repo / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\n", encoding="utf-8")

    return repo


def test_scan_counts_files_and_lines(sample_repo: Path):
    scanner = RepositoryScanner()
    result = scanner.scan(sample_repo)

    assert result.total_files == 2
    assert result.total_lines == 3
    assert {file.relative_path for file in result.files} == {"main.py", "README.md"}
    assert ".git" in result.ignored_directories
    assert "node_modules" in result.ignored_directories


def test_scan_aggregates_languages(sample_repo: Path):
    scanner = RepositoryScanner()
    result = scanner.scan(sample_repo)

    languages = {language.extension: language.file_count for language in result.languages}
    assert languages[".py"] == 1
    assert languages[".md"] == 1


def test_scan_raises_when_path_does_not_exist():
    scanner = RepositoryScanner()

    with pytest.raises(PathNotFoundError):
        scanner.scan("/path/that/does/not/exist")


def test_scan_raises_when_path_is_not_directory(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")
    scanner = RepositoryScanner()

    with pytest.raises(NotADirectoryError):
        scanner.scan(file_path)


def test_scan_skips_binary_files(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "text.txt").write_text("hello\n", encoding="utf-8")
    (repo / "binary.bin").write_bytes(b"\x00\x01\x02")

    scanner = RepositoryScanner()
    result = scanner.scan(repo)

    assert result.total_files == 1
    assert result.files[0].relative_path == "text.txt"


def test_scan_ignores_pytest_cache(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("x = 1\n", encoding="utf-8")

    pytest_cache = repo / ".pytest_cache" / "v" / "cache"
    pytest_cache.mkdir(parents=True)
    (pytest_cache / "nodeids").write_text('["tests/test_example.py::test_foo"]\n', encoding="utf-8")

    scanner = RepositoryScanner()
    result = scanner.scan(repo)

    assert result.total_files == 1
    assert result.files[0].relative_path == "main.py"
    assert ".pytest_cache" in result.ignored_directories
    assert all(".pytest_cache" not in file.relative_path for file in result.files)


def test_scan_skips_env_file(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("x = 1\n", encoding="utf-8")
    (repo / ".env").write_text("OPENAI_API_KEY=super-secret\n", encoding="utf-8")

    scanner = RepositoryScanner()
    result = scanner.scan(repo)

    assert result.total_files == 1
    assert result.files[0].relative_path == "main.py"
    assert ".env" in result.ignored_files


def test_scan_skips_env_local_file(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    (repo / ".env.local").write_text("SECRET=local-only\n", encoding="utf-8")

    scanner = RepositoryScanner()
    result = scanner.scan(repo)

    assert {file.relative_path for file in result.files} == {"app.py"}
    assert ".env.local" in result.ignored_files


def test_scan_skips_pem_and_key_files(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "server.pem").write_text("-----BEGIN CERT-----\n", encoding="utf-8")
    (repo / "private.key").write_text("private-key-data\n", encoding="utf-8")

    scanner = RepositoryScanner()
    result = scanner.scan(repo)

    assert {file.relative_path for file in result.files} == {"app.py"}
    assert "server.pem" in result.ignored_files
    assert "private.key" in result.ignored_files
