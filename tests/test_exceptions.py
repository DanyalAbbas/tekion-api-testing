import pytest
from tekion_api.exceptions import (
    TekionError,
    AuthError,
    NotFoundError,
    RateLimitError,
    TokenRateLimitError,
    ValidationError,
    ServerError,
    TokenExpiredError,
)


def test_all_errors_are_tekion_errors():
    """Every custom exception must be instanceof TekionError."""
    assert issubclass(AuthError, TekionError)
    assert issubclass(NotFoundError, TekionError)
    assert issubclass(RateLimitError, TekionError)
    assert issubclass(TokenRateLimitError, TekionError)
    assert issubclass(ValidationError, TekionError)
    assert issubclass(ServerError, TekionError)
    assert issubclass(TokenExpiredError, TekionError)


def test_token_rate_limit_is_rate_limit():
    """TokenRateLimitError must inherit from RateLimitError."""
    assert issubclass(TokenRateLimitError, RateLimitError)


def test_token_expired_is_auth_error():
    """TokenExpiredError must inherit from AuthError (fatal auth failure)."""
    assert issubclass(TokenExpiredError, AuthError)


def test_nesting_works():
    """Catch TekionError catches all subtypes."""
    for exc in [AuthError("a"), NotFoundError("b"), RateLimitError("c"),
                ValidationError("d"), ServerError("e")]:
        assert isinstance(exc, TekionError)


def test_message_preserved():
    """Exception message string is preserved."""
    msg = "something went wrong"
    e = TekionError(msg)
    assert str(e) == msg
