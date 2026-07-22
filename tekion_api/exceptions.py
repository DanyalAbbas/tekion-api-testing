class TekionError(Exception):
    """Base exception for all Tekion API errors."""
    pass


class AuthError(TekionError):
    """Authentication failure — token fetch denied or invalid credentials."""
    pass


class TokenExpiredError(AuthError):
    """Fatal auth failure: token expired and refresh failed."""
    pass


class NotFoundError(TekionError):
    """Resource not found (404)."""
    pass


class RateLimitError(TekionError):
    """Rate limit exceeded (429)."""
    pass


class TokenRateLimitError(RateLimitError):
    """Token generation rate limit exceeded (20 per 15 min)."""
    pass


class ValidationError(TekionError):
    """Request validation failure (400/422)."""
    pass


class ServerError(TekionError):
    """Server-side error (5xx)."""
    pass
