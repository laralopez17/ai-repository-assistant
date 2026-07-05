from pathlib import PurePosixPath

SOURCE_TYPE_SOURCE = "source"
SOURCE_TYPE_TEST = "test"
SOURCE_TYPE_DOCS = "docs"
SOURCE_TYPE_CONFIG = "config"
SOURCE_TYPE_OTHER = "other"

SOURCE_ROOT_PREFIXES = ("app/", "src/", "lib/")
CONFIG_EXTENSIONS = {".ini", ".toml", ".yaml", ".yml", ".json", ".txt"}


def detect_source_type(file_path: str, extension: str) -> str:
    normalized_path = file_path.replace("\\", "/")
    path = PurePosixPath(normalized_path)
    file_name = path.name

    if normalized_path.startswith("tests/") or file_name.startswith("test_"):
        return SOURCE_TYPE_TEST

    if normalized_path.startswith(SOURCE_ROOT_PREFIXES):
        return SOURCE_TYPE_SOURCE

    normalized_extension = extension.lower()
    if normalized_extension == ".md":
        return SOURCE_TYPE_DOCS

    if normalized_extension in CONFIG_EXTENSIONS:
        return SOURCE_TYPE_CONFIG

    return SOURCE_TYPE_OTHER
