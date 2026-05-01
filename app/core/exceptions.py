from typing import Any, Optional

class AuthError(Exception):
    """
    Exception for authentication or authorization errors.
    """
    def __init__(self, detail: str, status_code: int = 401):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class ValidationError(Exception):
    """
    Exception for validation errors (input, data, etc).
    """
    def __init__(self, detail: str, status_code: int = 422):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class NotFoundError(Exception):
    """
    Exception for not found errors (resource missing).
    """
    def __init__(self, detail: str, status_code: int = 404):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class RateLimitError(Exception):
    """
    Exception for rate limiting (too many requests).
    """
    def __init__(self, detail: str, status_code: int = 429):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class KYCError(Exception):
    """
    Exception for KYC (identity verification) errors.
    """
    def __init__(self, detail: str, status_code: int = 403):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
