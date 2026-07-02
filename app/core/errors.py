class AppError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class PathNotFoundError(AppError):
    pass


class NotADirectoryError(AppError):
    pass
