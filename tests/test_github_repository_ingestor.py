import subprocess
from pathlib import Path

import pytest

from app.core.errors import (
    GitCloneError,
    GitCloneTimeoutError,
    GitHubRepositoryNotFoundError,
    GitNotInstalledError,
    InvalidGitHubUrlError,
)
from app.services.chunking_service import ChunkingService
from app.services.content_extractor import ContentExtractor
from app.services.fake_embedding_provider import FakeEmbeddingProvider
from app.services.github_repository_ingestor import GitHubRepositoryIngestor
from app.services.repository_indexer import RepositoryIndexer
from app.services.repository_scanner import RepositoryScanner
from app.services.sqlite_index_store import SQLiteIndexStore


def _build_ingestor(
    index_store: SQLiteIndexStore,
    clone,
) -> GitHubRepositoryIngestor:
    repository_indexer = RepositoryIndexer(
        scanner=RepositoryScanner(),
        content_extractor=ContentExtractor(),
        chunking_service=ChunkingService(),
        embedding_provider=FakeEmbeddingProvider(),
        index_store=index_store,
    )
    return GitHubRepositoryIngestor(repository_indexer, clone=clone)


def test_github_ingestor_reuses_indexing_pipeline(index_store):
    def fake_clone(url: str, destination: Path, timeout: int) -> None:
        destination.mkdir(parents=True)
        (destination / "chunking.py").write_text("chunk logic here\n", encoding="utf-8")

    ingestor = _build_ingestor(index_store, fake_clone)

    result = ingestor.index_github_repository("https://github.com/owner/repo")

    assert result.source == "github"
    assert result.github_url == "https://github.com/owner/repo"
    assert result.total_chunks_indexed == 1
    assert index_store.get_index(result.index_id).total_chunks_indexed == 1


def test_github_ingestor_cleans_up_temporary_directory(index_store):
    cloned_paths: list[Path] = []

    def fake_clone(url: str, destination: Path, timeout: int) -> None:
        cloned_paths.append(destination)
        destination.mkdir(parents=True)
        (destination / "app.py").write_text("chunk logic\n", encoding="utf-8")

    ingestor = _build_ingestor(index_store, fake_clone)
    ingestor.index_github_repository("https://github.com/owner/repo")

    assert cloned_paths
    assert not cloned_paths[0].exists()


def test_github_ingestor_raises_for_invalid_url(index_store):
    ingestor = _build_ingestor(index_store, lambda *_: None)

    with pytest.raises(InvalidGitHubUrlError):
        ingestor.index_github_repository("https://gitlab.com/owner/repo")


def test_github_ingestor_raises_for_clone_failure(index_store):
    def failing_clone(url: str, destination: Path, timeout: int) -> None:
        raise subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "clone"],
            stderr="remote: Repository not found.",
        )

    ingestor = _build_ingestor(index_store, failing_clone)

    with pytest.raises(GitHubRepositoryNotFoundError):
        ingestor.index_github_repository("https://github.com/owner/missing")


def test_github_ingestor_raises_for_clone_timeout(index_store):
    def timeout_clone(url: str, destination: Path, timeout: int) -> None:
        raise subprocess.TimeoutExpired(
            cmd=["git", "clone"],
            timeout=timeout,
        )

    ingestor = _build_ingestor(index_store, timeout_clone)

    with pytest.raises(GitCloneTimeoutError):
        ingestor.index_github_repository("https://github.com/owner/repo")


def test_github_ingestor_raises_for_missing_git(index_store):
    def missing_git_clone(url: str, destination: Path, timeout: int) -> None:
        raise FileNotFoundError("git")

    ingestor = _build_ingestor(index_store, missing_git_clone)

    with pytest.raises(GitNotInstalledError):
        ingestor.index_github_repository("https://github.com/owner/repo")


def test_github_ingestor_raises_for_unexpected_clone_failure(index_store):
    def failing_clone(url: str, destination: Path, timeout: int) -> None:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "clone"],
            stderr="unexpected network error",
        )

    ingestor = _build_ingestor(index_store, failing_clone)

    with pytest.raises(GitCloneError):
        ingestor.index_github_repository("https://github.com/owner/repo")
