# Tekion API Client Design — Customer Fetching & Creation

## Overview

Design and implement a Python API client for Tekion's Automotive Partner Cloud (APC), starting with Customer endpoints. This is the foundational library for AutoAdvisor AI — a voice agent that handles dealership service calls.

## Architecture

### Layered Design

```
config.py ──────────────────────┐
    ↓                            ↓
  auth.py ──→ exceptions.py    client.py
    ↓                            ↓
  services/base.py ←─────────────┘
    ↓
  services/customer.py
```

- **`config.py`**: Zero-dependency settings reader. Reads env vars, returns typed `TekionConfig`.
- **`auth.py`**: Token lifecycle manager. Caches JWTs in memory, respects 20-token/15-min rate limit, proactively refreshes near expiry.
- **`client.py`**: HTTP transport via `httpx`. Injects headers (app_id, Authorization, dealer_id). Handles 401 with one retry + force-refresh. Passes typed exceptions upward for 400/404/429/5xx.
- **`services/base.py`**: Abstract base with a `_request()` helper that tags every call by API tier (Open/Select/Premium) for observability.
- **`services/customer.py`**: Domain operations — search, get, create, update. No orchestration logic; each method maps cleanly to one endpoint call.
- **`exceptions.py`**: `TekionError` → `AuthError`, `NotFoundError`, `RateLimitError`, `ValidationError`, `ServerError`.

### Project Layout

```
tekion-api-testing/
├── pyproject.toml
├── .env.example
├── tekion_api/
│   ├── __init__.py
│   ├── config.py
│   ├── auth.py
│   ├── client.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   └── customer.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── customer.py
│   └── exceptions.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_client.py
│   └── services/
│       └── test_customer.py
└── scripts/
    └── demo_customer.py
```

## Authentication

### Token Lifecycle

`POST /openapi/public/tokens` with `app_id` + `secret_key` (form-urlencoded).

Response:
```json
{
  "status": "success",
  "data": {
    "token_type": "Bearer",
    "access_token": "eyJhbGci...",
    "expire_in": 86399,
    "expire_on": 1706086696,
    "issued_at": 1706000296
  }
}
```

- **`expire_on`** (epoch seconds) used as the authoritative expiry source.
- TokenCache: in-memory dict, keyed by `dealer_id` if per-dealer tokens needed later.
- Rate-limit guard: sliding 15-min window, limit 18/20 (buffer).
- Proactive refresh: if remaining TTL < 5 minutes, refresh on next call.
- Single retry on 401 responses: force-refresh token, retry exactly once.

## Customer API Surface

### Select — Get Customer by ID

`GET /openapi/v4.0.0/customers/{customerId}`

Returns full customer bundle. Used after caller identity is already resolved.

### Premium — Search Customers

`GET /openapi/v4.0.0/customers?phone={phone}&search={search}&firstName={fn}&lastName={ln}&email={email}`

Flexible search with cursor-based pagination via `nextFetchKey`. The `search` parameter matches across first name, last name, email, phone, and arcId.

### Open — Create Customer

`POST /openapi/v4.0.0/customers`

Minimal viable payload for voice-agent intake:
```json
{
  "status": "ACTIVE",
  "customerDetails": {
    "customerType": "INDIVIDUAL",
    "phoneCommunications": [{
      "phoneType": "MOBILE",
      "phone": { "countryCode": 1, "localNumber": "5551234567" },
      "usagePreference": { "preferred": true, "preferenceMapping": { "MARKETING": "NO", "TRANSACTION": "YES" } }
    }],
    "name": { "firstName": "John", "lastName": "Doe" }
  }
}
```

### Open — Update Customer

`PUT /openapi/v4.0.0/customers/{customerId}`

Same schema as Create. Used when caller provides corrected information.

### Response Handling

All models use Pydantic with `extra="ignore"` per Tekion's explicit instruction that future optional fields may be added. The response envelope follows two patterns:
- `{ status, data }` (auth endpoint)
- `{ meta, data }` (resource endpoints)

The generic `ApiEnvelope` model handles both.

## Customer Service

```python
def search_customers(phone: str) -> list[Customer]  # PREMIUM tier
def get_customer(customer_id: str) -> Customer       # SELECT tier
def create_customer(data: dict) -> Customer           # OPEN tier
def update_customer(id: str, data: dict) -> Customer  # OPEN tier
```

No orchestration logic in the service layer. The caller (voice agent) decides:
1. `search_customers(phone)` → first match wins, or no match → no customer
2. `create_customer(...)` → called explicitly if needed

## Error Handling

| HTTP Status | Exception | Client Behavior |
|-------------|-----------|-----------------|
| 200-299 | — | Parse and return |
| 400/422 | `ValidationError` | Let caller decide |
| 401 | — | Force-refresh token, retry once |
| 404 | `NotFoundError` | Let caller decide |
| 429 | `RateLimitError` | Let caller decide (no auto-retry) |
| 5xx | `ServerError` | Let caller decide |

## Testing

- Mock HTTP layer with `respx` (mock library for httpx)
- Test each layer in isolation (auth → client → service)
- Integration test flag (`pytest --integration`) for real sandbox calls later
- Test cases cover: success, 401 auto-refresh, 429, empty results, invalid credentials

## Out of Scope (for this phase)

- Vehicle endpoints
- Appointment endpoints
- Repair Order endpoints
- Async/WebSocket support
- Persistent token caching to disk
- Rate-limit backoff strategy (caller responsibility)
