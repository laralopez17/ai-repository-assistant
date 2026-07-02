from pathlib import Path

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
