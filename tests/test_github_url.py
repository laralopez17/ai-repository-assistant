import pytest

from app.core.errors import InvalidGitHubUrlError
from app.utils.github_url import validate_and_normalize_github_url


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/owner/repo",
        "https://github.com/owner/repo.git",
        "  https://github.com/owner/repo  ",
    ],
)
def test_validate_and_normalize_github_url_accepts_valid_urls(url: str):
    assert validate_and_normalize_github_url(url) == "https://github.com/owner/repo"


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/repo",
        "https://gitlab.com/owner/repo",
        "https://github.com/owner",
        "https://github.com/owner/repo/extra",
        "https://github.com/owner/repo?ref=main",
        "https://github.com/owner/repo#readme",
        "https://user:token@github.com/owner/repo",
        "git@github.com:owner/repo.git",
        "",
        "not-a-url",
    ],
)
def test_validate_and_normalize_github_url_rejects_invalid_urls(url: str):
    with pytest.raises(InvalidGitHubUrlError):
        validate_and_normalize_github_url(url)
