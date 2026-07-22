import httpx

from tekion_api.config import TekionConfig
from tekion_api.exceptions import (
    AuthError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    ServerError,
    TekionError,
)


class ApiClient:
    """HTTP client for Tekion APC APIs.

    Injects required headers (app_id, Authorization, dealer_id) on every request.
    Handles 401 by refreshing the token and retrying exactly once.
    Raises typed exceptions for error responses.
    """

    def __init__(
        self,
        config: TekionConfig,
        token_manager,
        dealer_id: str | None = None,
    ):
        self._config = config
        self._token_manager = token_manager
        self._dealer_id = dealer_id or config.default_dealer_id
        self._http = httpx.Client(timeout=60.0)

    def get(self, path: str, params: dict | None = None) -> dict:
        return self.request("GET", path, params=params)

    def post(self, path: str, json: dict | None = None) -> dict:
        return self.request("POST", path, json=json)

    def put(self, path: str, json: dict | None = None) -> dict:
        return self.request("PUT", path, json=json)

    def request(self, method: str, path: str, **kwargs) -> dict:
        """Execute an API request with header injection and 401 retry.

        Returns the parsed JSON body as a dict.
        """
        url = f"{self._config.base_url}{path}"
        token = self._token_manager.get_token()

        headers = kwargs.pop("headers", {})
        headers.setdefault("Content-Type", "application/json")
        headers["app_id"] = self._config.app_id
        headers["Authorization"] = f"Bearer {token}"
        headers["dealer_id"] = self._dealer_id

        try:
            response = self._http.request(method, url, headers=headers, **kwargs)
        except httpx.RequestError as exc:
            raise TekionError(f"Request failed: {exc}") from exc

        # 401 → force-refresh token and retry once
        if response.status_code == 401:
            fresh_token = self._token_manager.get_token()
            headers["Authorization"] = f"Bearer {fresh_token}"
            try:
                response = self._http.request(method, url, headers=headers, **kwargs)
            except httpx.RequestError as exc:
                raise TekionError(f"Request failed on retry: {exc}") from exc

            if response.status_code == 401:
                raise AuthError(
                    "Authentication failed after token refresh. "
                    "Check credentials and dealer_id."
                )

        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict:
        """Convert HTTP status codes to typed exceptions."""
        if 200 <= response.status_code < 300:
            return response.json()

        try:
            body = response.json()
            detail = body.get("data", {}).get("message", response.text)
        except Exception:
            detail = response.text

        if response.status_code == 400 or response.status_code == 422:
            raise ValidationError(f"Validation error (HTTP {response.status_code}): {detail}")
        if response.status_code == 404:
            raise NotFoundError(f"Resource not found (HTTP 404): {detail}")
        if response.status_code == 429:
            raise RateLimitError(f"Rate limit exceeded (HTTP 429): {detail}")

        if response.status_code >= 500:
            raise ServerError(f"Server error (HTTP {response.status_code}): {detail}")

        raise TekionError(f"Unexpected HTTP {response.status_code}: {detail}")
