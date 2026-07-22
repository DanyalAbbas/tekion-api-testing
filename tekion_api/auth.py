import time
import threading
from collections import deque

import httpx

from tekion_api.config import TekionConfig
from tekion_api.exceptions import AuthError, TokenRateLimitError, TekionError

TOKEN_ENDPOINT = "/public/tokens"
MAX_TOKEN_REQUESTS = 18  # buffer below hard limit of 20
RATE_LIMIT_WINDOW = 900  # 15 minutes in seconds
DEFAULT_MIN_TTL = 300    # 5 minutes in seconds


class _TokenCacheEntry:
    """Holds a single cached token with its expiry."""

    def __init__(self, token: str, expire_on: int):
        self.token = token
        self.expire_on = expire_on

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expire_on

    def ttl_remaining(self) -> int:
        return max(0, self.expire_on - int(time.time()))


class TokenManager:
    """Manages Tekion API bearer token lifecycle.

    Caches tokens in memory per dealer_id, enforces the 20-token-per-15-min
    rate limit, and proactively refreshes tokens that are near expiry.
    Thread-safe via a reentrant lock.
    """

    def __init__(
        self,
        config: TekionConfig,
        dealer_id: str | None = None,
        min_ttl_seconds: int = DEFAULT_MIN_TTL,
    ):
        self._config = config
        self._dealer_id = dealer_id or config.default_dealer_id
        self._min_ttl = min_ttl_seconds
        self._lock = threading.Lock()

        # Per-dealer token cache
        self._cache: dict[str, _TokenCacheEntry] = {}

        # Rate-limit tracking: deque of timestamps (epoch seconds)
        self._request_timestamps: deque[float] = deque()

        self._http_client = httpx.Client(timeout=30.0)

    def get_token(self) -> str:
        """Return a valid bearer token, fetching or refreshing if needed.

        Returns the token string (without 'Bearer ' prefix).
        Raises AuthError on invalid credentials, TokenRateLimitError when
        the token generation rate limit is exceeded.
        """
        with self._lock:
            entry = self._cache.get(self._dealer_id)

            if entry and not entry.is_expired and entry.ttl_remaining() > self._min_ttl:
                return entry.token

            # Need a new token — check rate limit first
            self._enforce_rate_limit()

            token, expire_on = self._fetch_token()
            self._cache[self._dealer_id] = _TokenCacheEntry(token, expire_on)
            self._request_timestamps.append(time.time())
            return token

    def _enforce_rate_limit(self) -> None:
        """Check we haven't exceeded the token request rate limit."""
        now = time.time()
        # Prune timestamps older than the window
        while self._request_timestamps and self._request_timestamps[0] < now - RATE_LIMIT_WINDOW:
            self._request_timestamps.popleft()

        if len(self._request_timestamps) >= MAX_TOKEN_REQUESTS:
            raise TokenRateLimitError(
                f"Token generation rate limit exceeded: {MAX_TOKEN_REQUESTS} tokens "
                f"issued in the last {RATE_LIMIT_WINDOW // 60} minutes. "
                f"Wait before requesting more tokens."
            )

    def _fetch_token(self) -> tuple[str, int]:
        """Make the HTTP POST to fetch a new token.

        Returns (access_token, expire_on_epoch).
        """
        url = f"{self._config.base_url}{TOKEN_ENDPOINT}"
        try:
            response = self._http_client.post(
                url,
                data={
                    "app_id": self._config.app_id,
                    "secret_key": self._config.secret_key,
                },
            )
        except httpx.RequestError as exc:
            raise TekionError(f"Token request failed: {exc}") from exc

        if response.status_code != 200:
            raise AuthError(
                f"Token request failed with status {response.status_code}: "
                f"{response.text}"
            )

        body = response.json()
        data = body.get("data", {})

        access_token = data.get("access_token")
        expire_on = data.get("expire_on")

        if not access_token or not expire_on:
            raise AuthError(
                f"Token response missing access_token or expire_on: {body}"
            )

        return access_token, int(expire_on)
