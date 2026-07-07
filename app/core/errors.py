class AppError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class PathNotFoundError(AppError):
    pass


class NotADirectoryError(AppError):
    pass


class InvalidChunkingConfigError(AppError):
    pass


class MissingApiKeyError(AppError):
    pass


class IndexNotFoundError(AppError):
    pass


class UnsupportedProviderError(AppError):
    pass


class EmbeddingProviderError(AppError):
    pass


class LLMProviderError(AppError):
    pass


class ChunkLimitExceededError(AppError):
    pass


class DatabaseError(AppError):
    pass
