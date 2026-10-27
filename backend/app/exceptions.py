"""Domain errors mapped to HTTP responses by the API."""


class AppError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthError(AppError):
    def __init__(self, message: str = "Could not validate credentials") -> None:
        super().__init__(message, 401)


class ForbiddenError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 403)


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, 404)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 409)


class BadRequestError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 422)
