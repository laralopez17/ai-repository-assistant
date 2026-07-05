import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MAX_FILE_SIZE_BYTES = 1_048_576
BINARY_SAMPLE_SIZE = 8192

DEFAULT_IGNORED_DIRECTORIES = frozenset({
    ".git",
    "node_modules",
    "dist",
    "build",
    "target",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
})

DEFAULT_IGNORED_FILES = frozenset({
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "secrets.json",
})

DEFAULT_IGNORED_FILE_GLOBS = (
    ".env.*",
    "*.pem",
    "*.key",
)

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
).strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
).strip()

MAX_CHUNKS_TO_EMBED = int(os.getenv("MAX_CHUNKS_TO_EMBED", "50"))
