import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from app.core.errors import (
    GitCloneError,
    GitCloneTimeoutError,
    GitHubRepositoryNotFoundError,
    GitNotInstalledError,
)
from app.domain.models import GitHubIndexResult
from app.services.repository_indexer import RepositoryIndexer
from app.utils.github_url import validate_and_normalize_github_url

CloneFunction = Callable[[str, Path, int], None]

DEFAULT_MAX_LINES_PER_CHUNK = 80
DEFAULT_OVERLAP_LINES = 10
DEFAULT_CLONE_TIMEOUT_SECONDS = 60


class GitHubRepositoryIngestor:
    def __init__(
        self,
        repository_indexer: RepositoryIndexer,
        clone_timeout: int = DEFAULT_CLONE_TIMEOUT_SECONDS,
        clone: CloneFunction | None = None,
    ) -> None:
        self._repository_indexer = repository_indexer
        self._clone_timeout = clone_timeout
        self._clone = clone or self._default_clone

    def index_github_repository(
        self,
        url: str,
        max_lines_per_chunk: int = DEFAULT_MAX_LINES_PER_CHUNK,
        overlap_lines: int = DEFAULT_OVERLAP_LINES,
    ) -> GitHubIndexResult:
        github_url = validate_and_normalize_github_url(url)

        with tempfile.TemporaryDirectory(prefix="github-clone-") as temp_dir:
            clone_path = Path(temp_dir) / "repo"
            self._run_clone(github_url, clone_path)
            repository_index = self._repository_indexer.index_repository(
                str(clone_path),
                max_lines_per_chunk,
                overlap_lines,
            )

        return GitHubIndexResult(
            index_id=repository_index.index_id,
            repository_path=repository_index.repository_path,
            total_chunks_indexed=repository_index.total_chunks_indexed,
            embedding_model=repository_index.embedding_model,
            github_url=github_url,
        )

    def _run_clone(self, github_url: str, destination: Path) -> None:
        try:
            self._clone(github_url, destination, self._clone_timeout)
        except FileNotFoundError as error:
            raise GitNotInstalledError("git executable is not available") from error
        except subprocess.TimeoutExpired as error:
            raise GitCloneTimeoutError(
                f"Timed out cloning repository after {self._clone_timeout} seconds"
            ) from error
        except subprocess.CalledProcessError as error:
            stderr = (error.stderr or "").lower()
            if "not found" in stderr or "does not exist" in stderr:
                raise GitHubRepositoryNotFoundError(
                    "GitHub repository not found or is not accessible"
                ) from error
            raise GitCloneError("Failed to clone GitHub repository") from error

    def _default_clone(self, github_url: str, destination: Path, timeout: int) -> None:
        subprocess.run(
            ["git", "clone", "--depth", "1", github_url, str(destination)],
            check=True,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
