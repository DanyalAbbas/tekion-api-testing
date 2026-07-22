# Tekion API Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a layered Python API client for Tekion APC Customer endpoints (fetch, create, update, search).

**Architecture:** Five-layer package: config → auth → client → models → services. Each layer depends only on the layers below it. HTTP via `httpx`, token caching in memory, Pydantic models with `extra="ignore"` for forward compatibility.

**Tech Stack:** Python 3.11+, httpx, pydantic, python-dotenv, respx (test mocking), pytest

## Global Constraints

- All Pydantic models must use `extra="ignore"` for forward compatibility with Tekion's API evolution.
- Tokens authenticated via `POST /openapi/public/tokens` with `app_id` + `secret_key` (form-urlencoded).
- Every API call includes three headers: `app_id`, `Authorization: Bearer <token>`, `dealer_id`.
- API base URL defaults to sandbox (`https://api-sandbox.tekioncloud.com/openapi`).
- Rate-limit guard: max 18 token requests per 15-minute sliding window (buffer below the 20 hard limit).
- Token refresh triggered when remaining TTL < 5 minutes.
- 401 responses trigger exactly one token force-refresh + retry; other error codes propagate as typed exceptions.
- `httpx` with sync client only (async deferred to later phase).

---
## File Structure

All files listed here; each task creates/modifies its subset.

```
tekion-api-testing/
├── pyproject.toml                 # Task 1 — project metadata, deps
├── .env.example                   # Task 1 — credential template
├── tekion_api/
│   ├── __init__.py                # Task 1 — package marker
│   ├── config.py                  # Task 3 — environment config
│   ├── auth.py                    # Task 4 — token lifecycle
│   ├── client.py                  # Task 5 — HTTP transport
│   ├── exceptions.py              # Task 2 — error hierarchy
│   ├── models/
│   │   ├── __init__.py            # Task 1 — package marker
│   │   ├── common.py              # Task 6 — ApiEnvelope, PaginationMeta
│   │   └── customer.py            # Task 6 — Customer, CreateCustomerRequest
│   └── services/
│       ├── __init__.py            # Task 1 — package marker
│       ├── base.py                # Task 7 — ServiceBase
│       └── customer.py            # Task 7 — CustomerService
├── tests/
│   ├── __init__.py                # Task 1 — package marker
│   ├── conftest.py                # Task 3 — shared fixtures, respx mock
│   ├── test_exceptions.py         # Task 2 — hierarchy tests
│   ├── test_config.py             # Task 3 — config loading
│   ├── test_auth.py               # Task 4 — token manager
│   ├── test_client.py             # Task 5 — HTTP transport
│   ├── test_models.py             # Task 6 — model parsing
│   └── services/
│       ├── __init__.py            # Task 1 — package marker
│       └── test_customer.py       # Task 7 — customer service
└── scripts/
    └── demo_customer.py           # Task 8 — end-to-end demo
```

---
### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `tekion_api/__init__.py`
- Create: `tekion_api/models/__init__.py`
- Create: `tekion_api/services/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/services/__init__.py`

**Interfaces:**
- Consumes: nothing
- Produces: project skeleton with `pip install -e ".[dev]"` installable

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "tekion-api"
version = "0.1.0"
description = "Python client for Tekion Automotive Partner Cloud (APC) API"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27,<1",
    "pydantic>=2.0,<3",
    "python-dotenv>=1.0,<2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9",
    "pytest-asyncio>=0.23",
    "respx>=0.21,<1",
    "pytest-env>=1.0",
]
```

- [ ] **Step 2: Create .env.example**

```bash
TEKION_APP_ID=your_app_id_here
TEKION_SECRET_KEY=your_secret_key_here
TEKION_BASE_URL=https://api-sandbox.tekioncloud.com/openapi
TEKION_DEALER_ID=techmotors_4_0
```

- [ ] **Step 3: Create empty __init__.py files**

Create each of these as empty files:
- `tekion_api/__init__.py`
- `tekion_api/models/__init__.py`
- `tekion_api/services/__init__.py`
- `tests/__init__.py`
- `tests/services/__init__.py`

- [ ] **Step 4: Verify the package installs**

Run: `pip install -e ".[dev]"`
Expected: Package installed without errors. `python -c "import tekion_api"` succeeds.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example \
  tekion_api/__init__.py tekion_api/models/__init__.py tekion_api/services/__init__.py \
  tests/__init__.py tests/services/__init__.py
git commit -m "chore: scaffold tekion-api project"
```

---
### Task 2: Exception Hierarchy

**Files:**
- Create: `tekion_api/exceptions.py`
- Create: `tests/test_exceptions.py`

**Interfaces:**
- Consumes: nothing
- Produces: `TekionError`, `AuthError`, `NotFoundError`, `RateLimitError`, `TokenRateLimitError`, `ValidationError`, `ServerError`, `TokenExpiredError`

- [ ] **Step 1: Write the test for the hierarchy**

```python
# tests/test_exceptions.py
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
```

- [ ] **Step 2: Run test — expect failure**

Run: `pytest tests/test_exceptions.py -v`
Expected: ImportError — module not found

- [ ] **Step 3: Write exceptions.py**

```python
# tekion_api/exceptions.py
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
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_exceptions.py -v`
Expected: All 4 tests pass

- [ ] **Step 5: Commit**

```bash
git add tekion_api/exceptions.py tests/test_exceptions.py
git commit -m "feat: add exception hierarchy"
```

---
### Task 3: Configuration Module

**Files:**
- Create: `tekion_api/config.py`
- Create: `tests/test_config.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- Consumes: nothing
- Produces: `class TekionConfig(app_id, secret_key, base_url, default_dealer_id, token_cache_ttl)`, `load_config() -> TekionConfig`

- [ ] **Step 1: Write the tests**

```python
# tests/test_config.py
import os
from tekion_api.config import TekionConfig, load_config
from tekion_api.exceptions import TekionError


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("TEKION_APP_ID", "test-app")
    monkeypatch.setenv("TEKION_SECRET_KEY", "test-secret")
    monkeypatch.setenv("TEKION_DEALER_ID", "test-dealer")
    monkeypatch.setenv("TEKION_BASE_URL", "https://api-sandbox.tekioncloud.com/openapi")

    config = load_config()
    assert config.app_id == "test-app"
    assert config.secret_key == "test-secret"
    assert config.default_dealer_id == "test-dealer"
    assert config.base_url == "https://api-sandbox.tekioncloud.com/openapi"


def test_load_config_default_base_url(monkeypatch):
    """Defaults to sandbox when TEKION_BASE_URL not set."""
    monkeypatch.setenv("TEKION_APP_ID", "test-app")
    monkeypatch.setenv("TEKION_SECRET_KEY", "test-secret")
    monkeypatch.setenv("TEKION_DEALER_ID", "test-dealer")

    config = load_config()
    assert config.base_url == "https://api-sandbox.tekioncloud.com/openapi"


def test_load_config_missing_required(monkeypatch):
    """Raises TekionError when required env vars are missing."""
    monkeypatch.delenv("TEKION_APP_ID", raising=False)
    monkeypatch.delenv("TEKION_SECRET_KEY", raising=False)
    monkeypatch.delenv("TEKION_DEALER_ID", raising=False)

    with pytest.raises(TekionError, match="TEKION_APP_ID"):
        load_config()


def test_load_config_partial_missing(monkeypatch):
    """Raises TekionError listing all missing vars."""
    monkeypatch.setenv("TEKION_APP_ID", "test-app")
    monkeypatch.delenv("TEKION_SECRET_KEY", raising=False)
    monkeypatch.delenv("TEKION_DEALER_ID", raising=False)

    with pytest.raises(TekionError, match="TEKION_SECRET_KEY"):
        load_config()
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_config.py -v`
Expected: ImportError — config module not found

- [ ] **Step 3: Write config.py**

```python
# tekion_api/config.py
import os
from dataclasses import dataclass, field

from tekion_api.exceptions import TekionError

DEFAULT_BASE_URL = "https://api-sandbox.tekioncloud.com/openapi"
SANDBOX_BASE_URL = "https://api-sandbox.tekioncloud.com/openapi"
PRODUCTION_BASE_URL = "https://api.tekioncloud.com/openapi"


@dataclass(frozen=True)
class TekionConfig:
    app_id: str
    secret_key: str
    base_url: str = SANDBOX_BASE_URL
    default_dealer_id: str = ""
    token_cache_ttl: int = 82800  # 23 hours in seconds (safety margin below 24h)


def load_config() -> TekionConfig:
    """Load Tekion configuration from environment variables.

    Required:
        TEKION_APP_ID
        TEKION_SECRET_KEY
        TEKION_DEALER_ID

    Optional:
        TEKION_BASE_URL (defaults to sandbox)
        TEKION_TOKEN_CACHE_TTL (defaults to 82800)
    """
    missing = []
    app_id = os.getenv("TEKION_APP_ID")
    if not app_id:
        missing.append("TEKION_APP_ID")

    secret_key = os.getenv("TEKION_SECRET_KEY")
    if not secret_key:
        missing.append("TEKION_SECRET_KEY")

    dealer_id = os.getenv("TEKION_DEALER_ID")
    if not dealer_id:
        missing.append("TEKION_DEALER_ID")

    if missing:
        raise TekionError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Set them in .env or export them."
        )

    base_url = os.getenv("TEKION_BASE_URL", SANDBOX_BASE_URL)
    ttl_str = os.getenv("TEKION_TOKEN_CACHE_TTL", "")
    ttl = int(ttl_str) if ttl_str else 82800

    return TekionConfig(
        app_id=app_id,
        secret_key=secret_key,
        base_url=base_url,
        default_dealer_id=dealer_id,
        token_cache_ttl=ttl,
    )
```

- [ ] **Step 4: Write conftest.py with shared fixture for config**

```python
# tests/conftest.py
import pytest
from tekion_api.config import TekionConfig


@pytest.fixture
def sandbox_config():
    return TekionConfig(
        app_id="test-app-id",
        secret_key="test-secret-key",
        base_url="https://api-sandbox.tekioncloud.com/openapi",
        default_dealer_id="techmotors_4_0",
    )
```

- [ ] **Step 5: Run tests — expect pass**

Run: `pytest tests/test_config.py -v`
Expected: All 4 tests pass

- [ ] **Step 6: Commit**

```bash
git add tekion_api/config.py tests/test_config.py tests/conftest.py
git commit -m "feat: add config module"
```

---
### Task 4: Authentication / Token Manager

**Files:**
- Create: `tekion_api/auth.py`
- Create: `tests/test_auth.py`

**Interfaces:**
- Consumes: `TekionConfig`, `AuthError`, `TokenRateLimitError`, `TekionError`
- Produces: `class TokenManager(config, dealer_id="")`, `tm.get_token() -> str`

```python
tm = TokenManager(config)       # uses default_dealer_id
tm = TokenManager(config, dealer_id="other_dealer")  # per-dealer cache key
token = tm.get_token()          # returns "eyJhbGci..." bearer token string
```

- [ ] **Step 1: Write tests**

```python
# tests/test_auth.py
import time
import respx
import pytest
from httpx import Response

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
        route.respond(200, json=_token_response(expire_in=1))

        tm = TokenManager(sandbox_config, min_ttl_seconds=0)
        # With 1s expiry, every call triggers a refresh
        # 19th call should raise the rate limit error
        for _ in range(18):
            tm.get_token()
            time.sleep(0.01)  # ensure slightly different timestamps

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
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_auth.py -v`
Expected: ImportError — auth module not found

- [ ] **Step 3: Write auth.py**

```python
# tekion_api/auth.py
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
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_auth.py -v`
Expected: All 7 tests pass

- [ ] **Step 5: Commit**

```bash
git add tekion_api/auth.py tests/test_auth.py
git commit -m "feat: add token manager with rate-limit enforcement"
```

---
### Task 5: HTTP Client Layer

**Files:**
- Create: `tekion_api/client.py`
- Create: `tests/test_client.py`

**Interfaces:**
- Consumes: `TokenManager.get_token()`, `TekionConfig`, all exceptions
- Produces: `class ApiClient(config, token_manager, dealer_id="")`
  - `client.request(method, path, **kwargs) -> dict`  (returns the full JSON response body)
  - `client.get(path, params) -> dict`
  - `client.post(path, json) -> dict`
  - `client.put(path, json) -> dict`

The client auto-injects `app_id`, `Authorization: Bearer <token>`, `dealer_id`, and `Content-Type: application/json` headers. On 401, it calls `token_manager.get_token()` (which force-refreshes) and retries exactly once.

- [ ] **Step 1: Write tests**

```python
# tests/test_client.py
import respx
import pytest
from httpx import Response, RequestError

from tekion_api.client import ApiClient
from tekion_api.exceptions import AuthError, NotFoundError, RateLimitError, ValidationError, ServerError, TekionError


class TestApiClient:
    def test_get_success(self, sandbox_config, respx_mock):
        """GET returns parsed JSON body."""
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-123"
        ).respond(200, json={"data": {"id": "cust-123", "firstName": "John"}})

        client = ApiClient(sandbox_config, token_manager=_dummy_tm())
        result = client.get("/v4.0.0/customers/cust-123")

        assert result["data"]["id"] == "cust-123"
        assert route.called

    def test_post_success(self, sandbox_config, respx_mock):
        """POST returns parsed JSON body."""
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
        ).respond(201, json={"data": {"id": "new-cust"}})

        client = ApiClient(sandbox_config, token_manager=_dummy_tm())
        result = client.post("/v4.0.0/customers", json={"name": "Jane"})

        assert result["data"]["id"] == "new-cust"
        assert route.called

    def test_injects_headers(self, sandbox_config, respx_mock):
        """All required headers are present on every request."""
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(200, json={"data": {}})

        client = ApiClient(sandbox_config, token_manager=_dummy_tm())
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

        # Token manager that returns a new token on refresh
        tm = _refreshable_tm()
        client = ApiClient(sandbox_config, token_manager=tm)
        result = client.get("/v4.0.0/customers/cust-1")

        assert result["data"]["id"] == "cust-1"
        assert first.called
        assert second.called
        # Token manager should have been asked for a fresh token
        assert tm.refresh_count == 1

    def test_401_twice_raises_auth_error(self, sandbox_config, respx_mock):
        """If the retry also gets 401, raise AuthError."""
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(401, json={"status": "error"})

        client = ApiClient(sandbox_config, token_manager=_dummy_tm())
        with pytest.raises(AuthError, match="Authentication failed after refresh"):
            client.get("/v4.0.0/customers/cust-1")
        assert route.call_count == 2

    def test_404_raises_not_found(self, sandbox_config, respx_mock):
        """404 raises NotFoundError."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/missing"
        ).respond(404, json={"status": "error"})

        client = ApiClient(sandbox_config, token_manager=_dummy_tm())
        with pytest.raises(NotFoundError):
            client.get("/v4.0.0/customers/missing")

    def test_429_raises_rate_limit(self, sandbox_config, respx_mock):
        """429 raises RateLimitError."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(429, json={"status": "error"})

        client = ApiClient(sandbox_config, token_manager=_dummy_tm())
        with pytest.raises(RateLimitError):
            client.get("/v4.0.0/customers/cust-1")

    def test_400_raises_validation_error(self, sandbox_config, respx_mock):
        """400 raises ValidationError."""
        respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
        ).respond(400, json={"status": "error"})

        client = ApiClient(sandbox_config, token_manager=_dummy_tm())
        with pytest.raises(ValidationError):
            client.post("/v4.0.0/customers", json={"bad": "data"})

    def test_500_raises_server_error(self, sandbox_config, respx_mock):
        """5xx raises ServerError."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(500, json={"status": "error"})

        client = ApiClient(sandbox_config, token_manager=_dummy_tm())
        with pytest.raises(ServerError):
            client.get("/v4.0.0/customers/cust-1")

    def test_put_request(self, sandbox_config, respx_mock):
        """PUT sends JSON body correctly."""
        route = respx_mock.put(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-1"
        ).respond(200, json={"data": {"id": "cust-1", "firstName": "Updated"}})

        client = ApiClient(sandbox_config, token_manager=_dummy_tm())
        result = client.put("/v4.0.0/customers/cust-1", json={"firstName": "Updated"})

        assert result["data"]["firstName"] == "Updated"
        assert route.called
```


- [ ] **Step 2: Add test helper functions to conftest.py**

Add to end of `tests/conftest.py`:

```python
# --- Test helpers for client tests ---

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


@pytest.fixture
def _dummy_tm():
    return _DummyTokenManager()


@pytest.fixture
def _refreshable_tm():
    return _RefreshableTokenManager()
```

- [ ] **Step 3: Write client.py**

```python
# tekion_api/client.py
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
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_client.py -v`
Expected: All 9 tests pass

- [ ] **Step 5: Commit**

```bash
git add tekion_api/client.py tests/test_client.py
git commit -m "feat: add HTTP client with 401 retry and typed exceptions"
```

---
### Task 6: Models

**Files:**
- Create: `tekion_api/models/common.py`
- Create: `tekion_api/models/customer.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: pydantic.BaseModel
- Produces:
  - `ApiEnvelope(status, meta, data)` — flexible response wrapper with `extra="ignore"`
  - `Customer(id, first_name, last_name, phone, ...)` — flattened customer with `extra="ignore"`
  - `CreateCustomerRequest(...)` — builds the nested Tekion JSON payload from flat inputs
  - `UpdateCustomerRequest(...)` — same schema, requires customer ID

- [ ] **Step 1: Write tests**

```python
# tests/test_models.py
import pytest
from pydantic import ValidationError

from tekion_api.models.common import ApiEnvelope
from tekion_api.models.customer import Customer, CreateCustomerRequest


class TestApiEnvelope:
    def test_status_data_pattern(self):
        """Handle {status, data} envelope from auth endpoints."""
        env = ApiEnvelope.model_validate({
            "status": "success",
            "data": {"token": "abc", "expire_on": 12345},
        })
        assert env.status == "success"
        assert env.data["token"] == "abc"

    def test_meta_data_pattern(self):
        """Handle {meta, data} envelope from resource endpoints."""
        env = ApiEnvelope.model_validate({
            "meta": {"nextFetchKey": "abc123"},
            "data": [{"id": "1"}, {"id": "2"}],
        })
        assert env.meta["nextFetchKey"] == "abc123"
        assert len(env.data) == 2

    def test_extra_fields_ignored(self):
        """Future unknown fields do NOT cause validation errors."""
        env = ApiEnvelope.model_validate({
            "status": "success",
            "data": {},
            "newFutureField": "someValue",
            "anotherFutureField": {"nested": 1},
        })
        assert env.status == "success"


class TestCustomer:
    def test_minimal_customer(self):
        """Customer can be created from a subset of fields."""
        c = Customer.model_validate({
            "id": "cust-123",
            "firstName": "John",
            "lastName": "Doe",
        })
        assert c.id == "cust-123"
        assert c.first_name == "John"

    def test_customer_unknown_fields_ignored(self):
        """Extra fields in the response are silently ignored."""
        c = Customer.model_validate({
            "id": "cust-1",
            "firstName": "Jane",
            "someNewTekionField": "should-not-break",
            "anotherNewField": {"nested": True},
        })
        assert c.id == "cust-1"
        assert c.first_name == "Jane"

    def test_customer_empty_id(self):
        """Customer with no ID (incomplete response) is still parseable."""
        c = Customer.model_validate({"firstName": "NoId"})
        assert c.first_name == "NoId"
        assert c.id is None

    def test_name_fields_mapped(self):
        """Response firstName -> first_name, lastName -> last_name."""
        c = Customer.model_validate({
            "firstName": "Alice",
            "lastName": "Smith",
            "phone": "555-0100",
            "email": "alice@example.com",
        })
        assert c.first_name == "Alice"
        assert c.last_name == "Smith"
        assert c.phone == "555-0100"
        assert c.email == "alice@example.com"


class TestCreateCustomerRequest:
    def test_minimal_payload(self):
        """CreateCustomerRequest produces the minimal nested JSON."""
        req = CreateCustomerRequest(
            first_name="John",
            last_name="Doe",
            phone="5551234567",
            country_code=1,
        )
        payload = req.to_dict()

        assert payload["status"] == "ACTIVE"
        assert payload["customerDetails"]["customerType"] == "INDIVIDUAL"
        assert payload["customerDetails"]["name"]["firstName"] == "John"
        assert payload["customerDetails"]["name"]["lastName"] == "Doe"
        assert payload["customerDetails"]["phoneCommunications"][0]["phone"]["countryCode"] == 1
        assert payload["customerDetails"]["phoneCommunications"][0]["phone"]["localNumber"] == "5551234567"

    def test_payload_is_serializable(self):
        """to_dict() returns JSON-serializable dict (no Pydantic models)."""
        req = CreateCustomerRequest(
            first_name="Jane",
            last_name="Smith",
            phone="555-9876",
        )
        import json
        payload = req.to_dict()
        # Should not raise
        json.dumps(payload)

    def test_requires_first_name(self):
        """first_name is required."""
        with pytest.raises(ValidationError):
            CreateCustomerRequest(last_name="Smith", phone="555-0000")

    def test_requires_last_name(self):
        """last_name is required."""
        with pytest.raises(ValidationError):
            CreateCustomerRequest(first_name="John", phone="555-0000")

    def test_requires_phone(self):
        """phone is required."""
        with pytest.raises(ValidationError):
            CreateCustomerRequest(first_name="John", last_name="Doe")
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_models.py -v`
Expected: ImportError — modules not found

- [ ] **Step 3: Write models/common.py**

```python
# tekion_api/models/common.py
from pydantic import BaseModel


class ApiEnvelope(BaseModel):
    """Generic Tekion API response envelope.

    Handles both patterns:
      - { "status": "success", "data": { ... } }
      - { "meta": { ... }, "data": [ ... ] }

    Uses extra="ignore" per Tekion's guidance that new optional fields
    may be added to responses over time.
    """
    model_config = {"extra": "ignore"}

    status: str | None = None
    meta: dict | None = None
    data: dict | list | None = None


class PaginationMeta(BaseModel):
    """Cursor-based pagination metadata from list endpoints."""
    model_config = {"extra": "ignore"}

    next_fetch_key: str | None = None
    total_count: int | None = None
```

- [ ] **Step 4: Write models/customer.py**

```python
# tekion_api/models/customer.py
from pydantic import BaseModel, Field


class Customer(BaseModel):
    """A Tekion customer record.

    Fields are flattened / snake_cased from Tekion's camelCase response.
    Only fields relevant to the voice agent use case are modeled.
    New fields from Tekion are silently ignored.
    """
    model_config = {"extra": "ignore"}

    id: str | None = None
    first_name: str | None = Field(None, alias="firstName")
    last_name: str | None = Field(None, alias="lastName")
    phone: str | None = None
    email: str | None = None
    customer_type: str | None = Field(None, alias="customerType")
    status: str | None = None

    def populate_by_name(self) -> "Customer":
        """Allow both alias and field-name population."""
        return self


class CreateCustomerRequest(BaseModel):
    """Builds the minimal Tekion Create Customer payload.

    Only includes fields necessary for voice-agent intake.
    """
    first_name: str
    last_name: str
    phone: str
    country_code: int = 1

    def to_dict(self) -> dict:
        """Convert to the nested Tekion JSON structure."""
        return {
            "status": "ACTIVE",
            "customerDetails": {
                "customerType": "INDIVIDUAL",
                "phoneCommunications": [
                    {
                        "phoneType": "MOBILE",
                        "phone": {
                            "countryCode": self.country_code,
                            "localNumber": self.phone,
                        },
                        "usagePreference": {
                            "preferred": True,
                            "preferenceMapping": {
                                "MARKETING": "NO",
                                "TRANSACTION": "YES",
                            },
                        },
                    }
                ],
                "name": {
                    "firstName": self.first_name,
                    "lastName": self.last_name,
                },
            },
        }


class UpdateCustomerRequest(CreateCustomerRequest):
    """Same payload structure as Create, but the caller supplies the ID to the service method."""
    pass
```

- [ ] **Step 5: Run tests — expect pass**

Run: `pytest tests/test_models.py -v`
Expected: All 10 tests pass

- [ ] **Step 6: Commit**

```bash
git add tekion_api/models/__init__.py tekion_api/models/common.py tekion_api/models/customer.py tests/test_models.py
git commit -m "feat: add API models with extra='ignore' for forward compat"
```

---
### Task 7: Base Service + Customer Service

**Files:**
- Create: `tekion_api/services/base.py`
- Create: `tekion_api/services/customer.py`
- Create: `tests/services/test_customer.py`

**Interfaces:**
- Consumes: `ApiClient`, `Customer`, `CreateCustomerRequest`, `NotFoundError`
- Produces: `class ServiceBase(client)`, `class CustomerService(client, dealer_id)`
  - `customer_service.search_customers(phone) -> list[Customer]`  — PREMIUM tier
  - `customer_service.get_customer(customer_id) -> Customer`      — SELECT tier
  - `customer_service.create_customer(first_name, last_name, phone, ...) -> Customer`  — OPEN tier
  - `customer_service.update_customer(customer_id, data) -> Customer`  — OPEN tier

- [ ] **Step 1: Write tests**

```python
# tests/services/test_customer.py
import respx
import pytest
from httpx import Response

from tekion_api.services.customer import CustomerService
from tekion_api.models.customer import Customer
from tekion_api.exceptions import NotFoundError, ValidationError


CUSTOMER_SEARCH_RESPONSE = {
    "meta": {"nextFetchKey": None},
    "data": [
        {
            "id": "cust-001",
            "firstName": "John",
            "lastName": "Doe",
            "phone": "555-0100",
            "email": "john@example.com",
        },
        {
            "id": "cust-002",
            "firstName": "Jane",
            "lastName": "Smith",
            "phone": "555-0200",
            "email": "jane@example.com",
        },
    ],
}

SINGLE_CUSTOMER_RESPONSE = {
    "data": {
        "id": "cust-001",
        "firstName": "John",
        "lastName": "Doe",
        "phone": "555-0100",
        "email": "john@example.com",
        "status": "ACTIVE",
    }
}


@pytest.fixture
def customer_service(sandbox_config, _dummy_tm):
    from tekion_api.client import ApiClient
    client = ApiClient(sandbox_config, token_manager=_dummy_tm)
    return CustomerService(client)


class TestCustomerService:
    def test_search_by_phone_found(self, customer_service, respx_mock):
        """search_customers returns list of Customer objects."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers?phone=555-0100"
        ).respond(200, json=CUSTOMER_SEARCH_RESPONSE)

        results = customer_service.search_customers(phone="555-0100")

        assert len(results) == 2
        assert results[0].id == "cust-001"
        assert results[0].first_name == "John"
        assert results[1].id == "cust-002"

    def test_search_by_phone_not_found(self, customer_service, respx_mock):
        """search_customers returns empty list when no match."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers?phone=555-9999"
        ).respond(200, json={"meta": {}, "data": []})

        results = customer_service.search_customers(phone="555-9999")
        assert results == []

    def test_search_by_phone_with_name(self, customer_service, respx_mock):
        """Search can combine phone and name filters."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
            "?phone=555-0100&firstName=John"
        ).respond(200, json={"meta": {}, "data": [CUSTOMER_SEARCH_RESPONSE["data"][0]]})

        results = customer_service.search_customers(phone="555-0100", first_name="John")
        assert len(results) == 1
        assert results[0].first_name == "John"

    def test_search_by_email(self, customer_service, respx_mock):
        """Search can use email filter."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
            "?email=john@example.com"
        ).respond(200, json={"meta": {}, "data": [CUSTOMER_SEARCH_RESPONSE["data"][0]]})

        results = customer_service.search_customers(email="john@example.com")
        assert len(results) == 1

    def test_search_with_general_term(self, customer_service, respx_mock):
        """Search can use the general 'search' parameter."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
            "?search=John+Doe"
        ).respond(200, json={"meta": {}, "data": [CUSTOMER_SEARCH_RESPONSE["data"][0]]})

        results = customer_service.search_customers(search="John Doe")
        assert len(results) == 1

    def test_get_customer_found(self, customer_service, respx_mock):
        """get_customer returns a single Customer by ID."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-001"
        ).respond(200, json=SINGLE_CUSTOMER_RESPONSE)

        customer = customer_service.get_customer("cust-001")
        assert customer.id == "cust-001"
        assert customer.first_name == "John"

    def test_get_customer_not_found(self, customer_service, respx_mock):
        """get_customer raises NotFoundError for missing ID."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/missing-id"
        ).respond(404, json={"status": "error"})

        with pytest.raises(NotFoundError):
            customer_service.get_customer("missing-id")

    def test_create_customer_minimal(self, customer_service, respx_mock):
        """create_customer returns the created customer."""
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
        ).respond(201, json=SINGLE_CUSTOMER_RESPONSE)

        customer = customer_service.create_customer(
            first_name="John",
            last_name="Doe",
            phone="555-0100",
        )
        assert customer.id == "cust-001"
        assert customer.first_name == "John"
        assert route.called

    def test_create_customer_invalid(self, customer_service, respx_mock):
        """create_customer raises ValidationError on bad data."""
        respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
        ).respond(400, json={"status": "error", "data": {"message": "Invalid phone number"}})

        with pytest.raises(ValidationError, match="Invalid phone number"):
            customer_service.create_customer(
                first_name="John",
                last_name="Doe",
                phone="not-a-phone",
            )

    def test_update_customer(self, customer_service, respx_mock):
        """update_customer sends PUT and returns updated Customer."""
        updated_response = {**SINGLE_CUSTOMER_RESPONSE, "data": {
            **SINGLE_CUSTOMER_RESPONSE["data"],
            "firstName": "Jonathan",
        }}
        route = respx_mock.put(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-001"
        ).respond(200, json=updated_response)

        customer = customer_service.update_customer(
            "cust-001",
            first_name="Jonathan",
            last_name="Doe",
            phone="555-0100",
        )
        assert customer.first_name == "Jonathan"
        assert route.called

    def test_update_customer_not_found(self, customer_service, respx_mock):
        """update_customer raises NotFoundError for missing ID."""
        respx_mock.put(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/missing"
        ).respond(404, json={"status": "error"})

        with pytest.raises(NotFoundError):
            customer_service.update_customer(
                "missing",
                first_name="No",
                last_name="One",
                phone="555-0000",
            )
```

- [ ] **Step 2: Write services/base.py**

```python
# tekion_api/services/base.py
from tekion_api.client import ApiClient


class ServiceBase:
    """Base class for all domain services.

    Provides shared infrastructure:
    - Client reference for API calls
    - API tier tagging for observability
    - Consistent error propagation
    """

    def __init__(self, client: ApiClient):
        self._client = client

    def _log_tier(self, tier: str, method: str, path: str) -> None:
        """Log the API call with its tier for observability."""
        # TODO: Replace with proper logging in production
        # print(f"[{tier}] {method} {path}")
        pass
```

- [ ] **Step 3: Write services/customer.py**

```python
# tekion_api/services/customer.py
import logging

from tekion_api.client import ApiClient
from tekion_api.models.customer import Customer, CreateCustomerRequest
from tekion_api.services.base import ServiceBase

logger = logging.getLogger(__name__)

CUSTOMER_PATH = "/v4.0.0/customers"


class CustomerService(ServiceBase):
    """Domain service for Tekion Customer operations.

    Every method maps to one API endpoint call. No orchestration logic.
    The caller decides how to sequence calls (search → create, etc.).
    """

    def __init__(self, client: ApiClient):
        super().__init__(client)

    def search_customers(
        self,
        *,
        phone: str | None = None,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        search: str | None = None,
        customer_type: str | None = None,
        **extra_params,
    ) -> list[Customer]:
        """Search customers by phone, email, name, or general search term.

        PREMIUM tier API. Returns list of matching customers (may be empty).
        """
        params = {}
        if phone is not None:
            params["phone"] = phone
        if email is not None:
            params["email"] = email
        if first_name is not None:
            params["firstName"] = first_name
        if last_name is not None:
            params["lastName"] = last_name
        if search is not None:
            params["search"] = search
        if customer_type is not None:
            params["customerType"] = customer_type
        # Allow extra filters like id, companyName, nextFetchKey
        params.update(extra_params)

        logger.info("Searching customers with filters: %s", {k: v for k, v in params.items() if k != "phone"})
        response = self._client.get(CUSTOMER_PATH, params=params)

        raw_data = response.get("data", [])
        if not raw_data:
            return []
        return [Customer.model_validate(c) for c in raw_data]

    def get_customer(self, customer_id: str) -> Customer:
        """Fetch a single customer by their Tekion customer ID.

        SELECT tier API. Raises NotFoundError if the ID doesn't exist.
        """
        logger.info("Fetching customer: %s", customer_id)
        response = self._client.get(f"{CUSTOMER_PATH}/{customer_id}")
        raw_data = response.get("data", {})
        return Customer.model_validate(raw_data)

    def create_customer(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        country_code: int = 1,
    ) -> Customer:
        """Create a new customer with minimal required fields.

        OPEN tier API. Returns the created Customer with assigned ID.
        """
        req = CreateCustomerRequest(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            country_code=country_code,
        )
        payload = req.to_dict()
        logger.info("Creating customer: %s %s", first_name, last_name)
        response = self._client.post(CUSTOMER_PATH, json=payload)
        raw_data = response.get("data", {})
        return Customer.model_validate(raw_data)

    def update_customer(
        self,
        customer_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        phone: str | None = None,
        country_code: int = 1,
    ) -> Customer:
        """Update an existing customer's details.

        OPEN tier API. Only provided fields are sent; omitted fields
        retain their existing values on the server.
        """
        current_data = self.get_customer(customer_id)

        req = CreateCustomerRequest(
            first_name=first_name or current_data.first_name or "",
            last_name=last_name or current_data.last_name or "",
            phone=phone or current_data.phone or "",
            country_code=country_code,
        )
        payload = req.to_dict()
        logger.info("Updating customer: %s", customer_id)
        response = self._client.put(f"{CUSTOMER_PATH}/{customer_id}", json=payload)
        raw_data = response.get("data", {})
        return Customer.model_validate(raw_data)
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/services/test_customer.py -v`
Expected: All 11 tests pass

- [ ] **Step 5: Commit**

```bash
git add tekion_api/services/base.py tekion_api/services/customer.py tests/services/test_customer.py
git commit -m "feat: add base service and customer service"
```

---
### Task 8: Demo Script

**Files:**
- Create: `scripts/demo_customer.py`

**Interfaces:**
- Consumes: everything above
- Produces: a CLI script `python scripts/demo_customer.py [command]`

- [ ] **Step 1: Write demo_customer.py**

```python
#!/usr/bin/env python3
"""Demo script for testing Tekion Customer APIs against the sandbox.

Usage:
    python scripts/demo_customer.py search --phone "5551234567"
    python scripts/demo_customer.py get    --id "cust-123"
    python scripts/demo_customer.py create --first "John" --last "Doe" --phone "5551234567"

Requires environment variables or .env file:
    TEKION_APP_ID, TEKION_SECRET_KEY, TEKION_DEALER_ID
"""
import sys
import os
import argparse
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from tekion_api.config import load_config
from tekion_api.auth import TokenManager
from tekion_api.client import ApiClient
from tekion_api.services.customer import CustomerService


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Tekion Customer API Demo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    search_parser = subparsers.add_parser("search", help="Search customers")
    search_parser.add_argument("--phone", help="Phone number to search")
    search_parser.add_argument("--email", help="Email to search")
    search_parser.add_argument("--name", help="Name to search (general search term)")

    # get
    get_parser = subparsers.add_parser("get", help="Get customer by ID")
    get_parser.add_argument("--id", required=True, help="Customer ID")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new customer")
    create_parser.add_argument("--first", required=True, help="First name")
    create_parser.add_argument("--last", required=True, help="Last name")
    create_parser.add_argument("--phone", required=True, help="Phone number")
    create_parser.add_argument("--country-code", type=int, default=1, help="Country code (default: 1)")

    args = parser.parse_args()

    # Boot the stack
    config = load_config()
    token_manager = TokenManager(config)
    client = ApiClient(config, token_manager)
    customer_service = CustomerService(client)

    try:
        if args.command == "search":
            params = {}
            if args.phone:
                params["phone"] = args.phone
            if args.email:
                params["email"] = args.email
            if args.name:
                params["search"] = args.name

            if not params:
                print("Error: provide at least one of --phone, --email, or --name")
                sys.exit(1)

            customers = customer_service.search_customers(**params)
            if customers:
                print(f"Found {len(customers)} customer(s):")
                for c in customers:
                    print(f"  [{c.id}] {c.first_name} {c.last_name} — {c.phone} — {c.email}")
            else:
                print("No customers found.")

        elif args.command == "get":
            customer = customer_service.get_customer(args.id)
            print(f"Customer: {customer.first_name} {customer.last_name}")
            print(f"  ID:    {customer.id}")
            print(f"  Phone: {customer.phone}")
            print(f"  Email: {customer.email}")
            print(f"  Type:  {customer.customer_type}")
            print(f"  Status: {customer.status}")

        elif args.command == "create":
            customer = customer_service.create_customer(
                first_name=args.first,
                last_name=args.last,
                phone=args.phone,
                country_code=args.country_code,
            )
            print(f"Created customer: [{customer.id}] {customer.first_name} {customer.last_name}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make script executable and verify imports**

```bash
chmod +x scripts/demo_customer.py
python -c "from tekion_api.services.customer import CustomerService; print('imports OK')"
```

Expected: "imports OK"

- [ ] **Step 3: Commit**

```bash
git add scripts/demo_customer.py
git commit -m "feat: add demo script for Customer API"
```

---
### Task 9: Full Test Suite Verification

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass (30+ tests across 6 test files)

- [ ] **Step 2: Quick smoke test of the demo script (dry-run, no API call)**

Run: `python scripts/demo_customer.py --help`
Expected: Shows usage text with search/get/create commands

- [ ] **Step 3: Commit any final tweaks**

```bash
git add -A
git commit -m "chore: finalize full test suite"
```
