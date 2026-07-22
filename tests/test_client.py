import respx
import pytest

from tekion_api.client import ApiClient
from tekion_api.exceptions import AuthError, NotFoundError, RateLimitError, ValidationError, ServerError


class TestApiClient:
    def test_get_success(self, sandbox_config, respx_mock):
        """GET returns parsed JSON body."""
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-123"
        ).respond(200, json={"data": {"id": "cust-123", "firstName": "John"}})

        client = ApiClient(sandbox_config, token_manager=_DummyTokenManager())
        result = client.get("/v4.0.0/customers/cust-123")

        assert result["data"]["id"] == "cust-123"
        assert route.called

    def test_post_success(self, sandbox_config, respx_mock):
        """POST returns parsed JSON body."""
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
        ).respond(201, json={"data": {"id": "new-cust"}})

        client = ApiClient(sandbox_config, token_manager=_DummyTokenManager())
        result = client.post("/v4.0.0/customers", json={"name": "Jane"})

        assert result["data"]["id"] == "new-cust"
        assert route.called

    def test_injects_headers(self, sandbox_config, respx_mock):
        """All required headers are present on every request."""
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(200, json={"data": {}})

        client = ApiClient(sandbox_config, token_manager=_DummyTokenManager())
        client.get("/v4.0.0/customers/cust-1")

        request = route.calls[0].request
        assert request.headers["app_id"] == sandbox_config.app_id
        assert request.headers["authorization"] == "Bearer test-token"
        assert request.headers["dealer_id"] == sandbox_config.default_dealer_id
        assert request.headers["content-type"] == "application/json"

    def test_401_triggers_refresh_and_retry(self, sandbox_config, respx_mock):
        """401 response forces token refresh and retries exactly once."""
        # First request returns 401, second succeeds
        first = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(401, json={"status": "error"})
        second = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(200, json={"data": {"id": "cust-1"}})

        tm = _RefreshableTokenManager()
        client = ApiClient(sandbox_config, token_manager=tm)
        result = client.get("/v4.0.0/customers/cust-1")

        assert result["data"]["id"] == "cust-1"
        assert first.called
        assert second.called
        assert tm.refresh_count == 1

    def test_401_twice_raises_auth_error(self, sandbox_config, respx_mock):
        """If the retry also gets 401, raise AuthError."""
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(401, json={"status": "error"})

        client = ApiClient(sandbox_config, token_manager=_DummyTokenManager())
        with pytest.raises(AuthError, match="Authentication failed after token refresh"):
            client.get("/v4.0.0/customers/cust-1")
        assert route.call_count == 2

    def test_404_raises_not_found(self, sandbox_config, respx_mock):
        """404 raises NotFoundError."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/missing"
        ).respond(404, json={"status": "error"})

        client = ApiClient(sandbox_config, token_manager=_DummyTokenManager())
        with pytest.raises(NotFoundError):
            client.get("/v4.0.0/customers/missing")

    def test_429_raises_rate_limit(self, sandbox_config, respx_mock):
        """429 raises RateLimitError."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(429, json={"status": "error"})

        client = ApiClient(sandbox_config, token_manager=_DummyTokenManager())
        with pytest.raises(RateLimitError):
            client.get("/v4.0.0/customers/cust-1")

    def test_400_raises_validation_error(self, sandbox_config, respx_mock):
        """400 raises ValidationError."""
        respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
        ).respond(400, json={"status": "error"})

        client = ApiClient(sandbox_config, token_manager=_DummyTokenManager())
        with pytest.raises(ValidationError):
            client.post("/v4.0.0/customers", json={"bad": "data"})

    def test_500_raises_server_error(self, sandbox_config, respx_mock):
        """5xx raises ServerError."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(500, json={"status": "error"})

        client = ApiClient(sandbox_config, token_manager=_DummyTokenManager())
        with pytest.raises(ServerError):
            client.get("/v4.0.0/customers/cust-1")

    def test_put_request(self, sandbox_config, respx_mock):
        """PUT sends JSON body correctly."""
        route = respx_mock.put(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(200, json={"data": {"id": "cust-1", "firstName": "Updated"}})

        client = ApiClient(sandbox_config, token_manager=_DummyTokenManager())
        result = client.put("/v4.0.0/customers/cust-1", json={"firstName": "Updated"})

        assert result["data"]["firstName"] == "Updated"
        assert route.called


class _DummyTokenManager:
    """Returns a fixed token, never refreshes."""
    def get_token(self):
        return "test-token"


class _RefreshableTokenManager:
    """Tracks how many times get_token was called (proxy for refresh attempts)."""
    def __init__(self):
        self.refresh_count = 0

    def get_token(self):
        self.refresh_count += 1
        return "fresh-token"
