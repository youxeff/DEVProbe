"""Service errors contain safe messages, never upstream bodies or credentials."""


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502, headers: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.headers = headers or {}


class InvalidRepositoryURL(ServiceError, ValueError):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)
