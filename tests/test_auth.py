import time
import respx
import pytest

from tekion_api.auth import TokenManager
from tekion_api.exceptions import AuthError, TokenRateLimitError


def _token_response(expire_in: int = 86399):
    """Build a mock token response body."""
    now = int(time.time())
    return {
        "status": "success",
        "data": {
            "token_type": "Bearer",
            "access_token": "eyJhbGciOiJIUzI1NiJ9.test-token",
            "expire_in": expire_in,
            "expire_on": now + expire_in,
            "issued_at": now,
        },
    }


class TestTokenManager:
    def test_get_token_success(self, sandbox_config, respx_mock):
        """Returns a token string from the auth endpoint."""
        route = respx_mock.post("https://api-sandbox.tekioncloud.com/openapi/public/tokens")
        route.respond(200, json=_token_response())

        tm = TokenManager(sandbox_config)
        token = tm.get_token()

        assert token == "eyJhbGciOiJIUzI1NiJ9.test-token"
        assert route.called

    def test_get_token_caches_and_reuses(self, sandbox_config, respx_mock):
        """Calling get_token() twice within expiry returns cached token."""
        route = respx_mock.post("https://api-sandbox.tekioncloud.com/openapi/public/tokens")
        route.respond(200, json=_token_response())

        tm = TokenManager(sandbox_config)
        t1 = tm.get_token()
        t2 = tm.get_token()

        assert t1 == t2
        assert route.call_count == 1  # only one HTTP call

    def test_get_token_refreshes_when_expired(self, sandbox_config, respx_mock):
        """An expired token triggers a new token request."""
        route = respx_mock.post("https://api-sandbox.tekioncloud.com/openapi/public/tokens")
        # First token with 0 second expiry (already expired)
        route.respond(200, json=_token_response(expire_in=0))

        tm = TokenManager(sandbox_config, min_ttl_seconds=0)
        tm.get_token()  # fetches first token
        tm.get_token()  # should detect expiry and re-fetch

        assert route.call_count == 2

    def test_get_token_proactive_refresh(self, sandbox_config, respx_mock):
        """Token with <5min remaining triggers refresh on next call."""
        route = respx_mock.post("https://api-sandbox.tekioncloud.com/openapi/public/tokens")
        # Token that expires in 4 minutes (240s) — below 5-min threshold
        route.respond(200, json=_token_response(expire_in=240))

        tm = TokenManager(sandbox_config, min_ttl_seconds=300)
        tm.get_token()  # fetches first token
        tm.get_token()  # should see only 240s left (<300) and refresh

        assert route.call_count == 2

    def test_get_token_invalid_credentials(self, sandbox_config, respx_mock):
        """Invalid credentials raise AuthError."""
        route = respx_mock.post("https://api-sandbox.tekioncloud.com/openapi/public/tokens")
        route.respond(401, json={"status": "error", "data": {"message": "Invalid credentials"}})

        tm = TokenManager(sandbox_config)
        with pytest.raises(AuthError, match="Token request failed with status 401"):
            tm.get_token()

    def test_rate_limit_enforcement(self, sandbox_config, respx_mock):
        """Raises TokenRateLimitError when >18 tokens requested in 15 min."""
        route = respx_mock.post("https://api-sandbox.tekioncloud.com/openapi/public/tokens")
        # Use negative expiry so each token is already expired when checked
        route.respond(200, json=_token_response(expire_in=-1))

        tm = TokenManager(sandbox_config, min_ttl_seconds=0)
        # With expired tokens, every call triggers a fetch
        # 19th call should raise the rate limit error
        for _ in range(18):
            tm.get_token()

        with pytest.raises(TokenRateLimitError, match="18 tokens issued"):
            tm.get_token()

    def test_uses_per_dealer_cache(self, sandbox_config, respx_mock):
        """Different dealer_ids have separate token caches."""
        route = respx_mock.post("https://api-sandbox.tekioncloud.com/openapi/public/tokens")
        route.respond(200, json=_token_response())

        tm1 = TokenManager(sandbox_config, dealer_id="dealer_a")
        tm2 = TokenManager(sandbox_config, dealer_id="dealer_b")

        tm1.get_token()
        tm2.get_token()

        assert route.call_count == 2
