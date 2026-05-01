from typing import Any, Optional

class AppException(Exception):
    """
    Base exception for application errors.
    """
    def __init__(self, detail: str, status_code: int = 400):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)

class AuthError(AppException):
    """
    Exception for authentication or authorization errors.
    """
    def __init__(self, detail: str, status_code: int = 401):
        super().__init__(detail, status_code)

class ValidationError(AppException):
    """
    Exception for validation errors (input, data, etc).
    """
    def __init__(self, detail: str, status_code: int = 422):
        super().__init__(detail, status_code)

class NotFoundError(AppException):
    """
    Exception for not found errors (resource missing).
    """
    def __init__(self, detail: str, status_code: int = 404):
        super().__init__(detail, status_code)

class RateLimitError(AppException):
    """
    Exception for rate limiting (too many requests).
    """
    def __init__(self, detail: str, status_code: int = 429):
        super().__init__(detail, status_code)

class KYCError(AppException):
    """
    Exception for KYC (identity verification) errors.
    """
    def __init__(self, detail: str, status_code: int = 403):
        super().__init__(detail, status_code)
