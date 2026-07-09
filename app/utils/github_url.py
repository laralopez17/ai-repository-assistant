import re
from urllib.parse import urlparse

from app.core.errors import InvalidGitHubUrlError

GITHUB_HOST = "github.com"
OWNER_REPO_PATTERN = re.compile(r"^/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


def validate_and_normalize_github_url(url: str) -> str:
    stripped = url.strip()
    if not stripped:
        raise InvalidGitHubUrlError("GitHub URL is required")

    parsed = urlparse(stripped)

    if parsed.scheme != "https":
        raise InvalidGitHubUrlError("Only HTTPS GitHub URLs are supported")

    if parsed.netloc.lower() != GITHUB_HOST:
        raise InvalidGitHubUrlError("Only github.com repository URLs are supported")

    if parsed.username or parsed.password:
        raise InvalidGitHubUrlError("GitHub URLs must not contain credentials")

    if parsed.query or parsed.fragment:
        raise InvalidGitHubUrlError(
            "GitHub URLs must not contain query parameters or fragments"
        )

    match = OWNER_REPO_PATTERN.match(parsed.path)
    if not match:
        raise InvalidGitHubUrlError(
            "GitHub URL must be in the format https://github.com/owner/repo"
        )

    owner, repo = match.groups()
    if not owner or not repo:
        raise InvalidGitHubUrlError("GitHub URL must include owner and repository name")

    if ".." in owner or ".." in repo:
        raise InvalidGitHubUrlError("Invalid GitHub URL format")

    return f"https://{GITHUB_HOST}/{owner}/{repo}"
