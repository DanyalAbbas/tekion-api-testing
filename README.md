# Tekion API Client

Python client for Tekion's Automotive Partner Cloud (APC) API — the foundation for AutoAdvisor AI.

## Features

- Token lifecycle management with rate-limit enforcement (20 tokens / 15 min)
- Auto-refresh on 401 with exactly one retry
- Customer CRUD: search (Premium), get (Select), create (Open), update (Open)
- Layered architecture: config, auth, client, models, services
- Typed exception hierarchy for all API error states
- Forward-compatible — all models ignore unknown fields per Tekion's guidance

## Quick Start

```bash
# Install
uv sync --extra dev

# Set up credentials
cp .env.example .env
# Then edit .env with your Tekion app credentials

# Run tests
uv run pytest -v
```

---

## Usage Guide

### 1. Set Up Credentials

Edit your `.env` file with the credentials from your Tekion application:

```ini
TEKION_APP_ID=your_app_id_here
TEKION_SECRET_KEY=your_secret_key_here
TEKION_DEALER_ID=techmotors_4_0
TEKION_BASE_URL=https://api-sandbox.tekioncloud.com/openapi
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEKION_APP_ID` | Yes | — | Your app ID from APC My Applications |
| `TEKION_SECRET_KEY` | Yes | — | Secret key generated in APC |
| `TEKION_DEALER_ID` | Yes | — | Dealer ID (sandbox: `techmotors_4_0`) |
| `TEKION_BASE_URL` | No | Sandbox URL | Production: `https://api.tekioncloud.com/openapi` |

### 2. Token Authentication (Automatic)

Authentication happens automatically. The `TokenManager` handles everything:

```python
from tekion_api.config import load_config
from tekion_api.auth import TokenManager

config = load_config()
token_manager = TokenManager(config)

# Get a token (cached until 5 min before expiry, then auto-refreshed)
token = token_manager.get_token()  # Returns the JWT string
```

- Tokens are cached in memory and shared across all API calls
- Refreshed proactively when less than 5 minutes of TTL remain
- Rate-limited to 18 tokens per rolling 15-minute window (buffer below Tekion's 20-token limit)
- Thread-safe via a reentrant lock

### 3. Make API Calls

```python
from dotenv import load_dotenv
load_dotenv()

from tekion_api.config import load_config
from tekion_api.auth import TokenManager
from tekion_api.client import ApiClient

config = load_config()
token_manager = TokenManager(config)
client = ApiClient(config, token_manager)

# GET with query params
response = client.get("/v4.0.0/customers", params={"phone": "5551234567"})

# GET a single resource
response = client.get("/v4.0.0/customers/cust-123")

# POST with JSON body
response = client.post("/v4.0.0/customers", json={"status": "ACTIVE", ...})

# PUT with JSON body
response = client.put("/v4.0.0/customers/cust-123", json={"status": "ACTIVE", ...})
```

The raw `ApiClient` returns parsed JSON dicts. Use the service layer for typed objects.

### 4. Work with Customers (Service Layer)

The `CustomerService` provides typed domain methods with proper models:

```python
from tekion_api.services.customer import CustomerService

customer_service = CustomerService(client)
```

#### Search customers by phone

```python
customers = customer_service.search_customers(phone="5551234567")

for c in customers:
    print(f"{c.first_name} {c.last_name} — {c.phone} — {c.email}")
    # John Doe — +15551234567 — john@example.com
```

Returns a `list[Customer]` (empty list if no matches). The API accepts partial phone matches, so you may get multiple results.

#### Other search filters

```python
# By email
customer_service.search_customers(email="john@example.com")

# By name
customer_service.search_customers(first_name="John", last_name="Doe")

# General search (matches name, email, phone, arcId)
customer_service.search_customers(search="John")

# Combined filters
customer_service.search_customers(phone="5551234567", first_name="John")
```

#### Get customer by ID

```python
customer = customer_service.get_customer("cust-123")
# Raises NotFoundError if the ID doesn't exist
```

#### Create a customer

```python
customer = customer_service.create_customer(
    first_name="Jane",
    last_name="Smith",
    phone="5551234567",
    country_code=1,  # optional, defaults to 1
)

print(f"Created: {customer.id}")
# Created: a1b2c3d4-...
```

#### Update a customer

```python
updated = customer_service.update_customer(
    "cust-123",
    first_name="Janet",  # Only fields you want to change
    phone="555-9999",
)
```

### 5. Customer Model Fields

The `Customer` model flattens Tekion's nested API response. These fields are available on every customer object:

| Field | Type | Source in API Response |
|-------|------|-----------------------|
| `.id` | `str \| None` | Top-level `id` |
| `.display_id` | `str \| None` | Top-level `displayId` |
| `.first_name` | `str \| None` | `customerDetails.name.firstName` |
| `.last_name` | `str \| None` | `customerDetails.name.lastName` |
| `.phone` | `str \| None` | First `phoneCommunications[].phone.completeNumber` (falls back to `localNumber`) |
| `.email` | `str \| None` | First `emailCommunications[].email` |
| `.customer_type` | `str \| None` | `customerDetails.customerType` |
| `.status` | `str \| None` | Top-level `status` |

Unknown fields from Tekion are silently ignored — new fields added by Tekion in the future will never cause parsing errors.

### 6. Error Handling

Every API error raises a typed exception so you can handle specific cases:

```python
from tekion_api.exceptions import (
    AuthError,          # Invalid credentials or token
    NotFoundError,      # 404 — customer not found
    RateLimitError,     # 429 — API rate limit hit
    ValidationError,    # 400/422 — bad request data
    ServerError,        # 5xx — Tekion server issue
    TekionError,        # Base class — catch-all
)

try:
    customer = customer_service.get_customer("nonexistent-id")
except NotFoundError:
    print("Customer not found")
except TekionError as e:
    print(f"API error: {e}")
```

### 7. Demo Script

The project includes a CLI script for quick testing against the sandbox:

```bash
# Search customers
uv run python scripts/demo_customer.py search --phone "5551234567"

# Search by email
uv run python scripts/demo_customer.py search --email "john@example.com"

# Search by name
uv run python scripts/demo_customer.py search --name "John Doe"

# Get customer by ID
uv run python scripts/demo_customer.py get --id "cust-123"

# Create a new customer
uv run python scripts/demo_customer.py create --first "Jane" --last "Smith" --phone "5551234567"
```

### 8. Full Boot Sequence

The standard initialization for any application using the library:

```python
from dotenv import load_dotenv
load_dotenv()

from tekion_api.config import load_config
from tekion_api.auth import TokenManager
from tekion_api.client import ApiClient
from tekion_api.services.customer import CustomerService

# 1. Load settings from environment
config = load_config()

# 2. Create token manager (caches tokens in memory)
token_manager = TokenManager(config)

# 3. Create HTTP client (injects headers, handles retries)
client = ApiClient(config, token_manager)

# 4. Create domain service
customer_service = CustomerService(client)

# 5. Use it
customers = customer_service.search_customers(phone="5551234567")
```

## Project Structure

```
tekion_api/
  config.py         Environment variable loading, typed settings
  auth.py           Token lifecycle manager (caching, rate limits)
  client.py         HTTP transport with header injection and 401 retry
  exceptions.py     TekionError, AuthError, NotFoundError, etc.
  models/
    common.py       ApiEnvelope (flexible response wrapper)
    customer.py     Customer, CreateCustomerRequest
  services/
    base.py         Abstract service base
    customer.py     CustomerService (search, get, create, update)
```

## Testing

```bash
uv run pytest -v
```

Tests mock all HTTP calls via `respx` — no network access needed. 52 tests covering:
- Token caching, expiry, proactive refresh, rate-limit enforcement
- HTTP header injection, 401 retry, all error status codes
- Customer model parsing from real API response structure
- Customer service (search, get, create, update, not-found, invalid-input)
