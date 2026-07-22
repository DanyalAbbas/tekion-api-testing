# Tekion API Client

Python client for Tekion's Automotive Partner Cloud (APC) API — the foundation for **AutoAdvisor AI**, an intelligent voice agent for dealership service departments.

[![Tests](https://github.com/DanyalAbbas/tekion-api-testing/actions/workflows/ci.yml/badge.svg)](https://github.com/DanyalAbbas/tekion-api-testing/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Domains](#api-domains)
  - [1. Customer (Stage 1)](#1-customer)
  - [2. Vehicle Inventory (Stage 2)](#2-vehicle-inventory)
  - [3. Repair Order (Stages 3, 6, 7, 8)](#3-repair-order)
  - [4. Support — Transportation (Stage 4)](#4-support--transportation)
  - [5. Service Appointments (Stage 5)](#5-service-appointments)
- [Demo Scripts](#demo-scripts)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Postman Collection](#postman-collection)
- [Links](#links)

---

## Features

- **Token lifecycle management** with rate-limit enforcement (18 tokens / 15 min rolling window)
- **Auto-refresh on 401** with exactly one retry
- **5 API domains** — Customer, Vehicle, Repair Order, Support, Appointments
- **14 Repair Order endpoints** — search, get, create, jobs, operations, parts, invoices, status
- **Layered architecture** — config → auth → client → services
- **Typed exceptions** for all API error states
- **92 tests** — all HTTP calls mocked via `respx`
- **Forward-compatible** — all models ignore unknown fields

---

## Quick Start

```bash
# Clone
git clone https://github.com/DanyalAbbas/tekion-api-testing.git
cd tekion-api-testing

# Install with dev dependencies
uv sync --extra dev

# Set up credentials
cp .env.example .env
# Edit .env with your Tekion app credentials

# Run tests
uv run pytest -v
```

### Credentials

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

---

## Architecture

```
                        ┌─────────────────┐
                        │   .env          │
                        │  TEKION_APP_ID  │
                        │  TEKION_*_KEY   │
                        └────────┬────────┘
                                 ▼
┌────────────────────────────────────────────────┐
│  config.py: load_config() → TekionConfig       │
│  (dataclass: app_id, secret_key, base_url, id) │
└────────────────────┬───────────────────────────┘
                     ▼
┌────────────────────────────────────────────────┐
│  auth.py: TokenManager                         │
│  • In-memory cache per dealer_id               │
│  • Proactive refresh (<5min TTL)              │
│  • Rate limit: 18 tokens / 15 min             │
│  • Thread-safe                                │
└────────────────────┬───────────────────────────┘
                     ▼
┌────────────────────────────────────────────────┐
│  client.py: ApiClient                          │
│  • Injects headers (app_id, Auth, dealer_id)   │
│  • 401 → refresh + retry                       │
│  • Raises typed exceptions                     │
│  • GET / POST / PUT                            │
└────┬────────┬────────┬────────┬──────┬─────────┘
     ▼        ▼        ▼        ▼      ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌──────────┐
│Customer││Vehicle ││Repair  ││Support ││Appointment│
│Service ││Service ││Order   ││Service ││Service    │
│        ││        ││Service ││        ││           │
└────────┘└────────┘└────────┘└────────┘└──────────┘
```

---

## API Domains

### 1. Customer

**Service:** `tekion_api/services/customer.py` — `CustomerService`

| Method | Endpoint | Tier | Description |
|--------|----------|------|-------------|
| `search_customers()` | `GET /v4.0.0/customers` | Premium | Search by phone, email, name, or general term |
| `get_customer()` | `GET /v4.0.0/customers/{id}` | Select | Full customer bundle + vehicles |
| `create_customer()` | `POST /v4.0.0/customers` | Open | Create new customer |
| `update_customer()` | `PUT /v4.0.0/customers/{id}` | Open | Update existing customer |

```python
from tekion_api.services.customer import CustomerService

# Search by phone
customers = customer_service.search_customers(phone="5551234567")
for c in customers:
    print(f"{c.first_name} {c.last_name} — {c.phone}")

# Get by ID (includes vehicles)
customer = customer_service.get_customer("cust-123")
for v in customer.vehicles:
    print(f"  {v.year} {v.make} {v.model} — {v.vin}")

# Create
customer = customer_service.create_customer(
    first_name="Jane", last_name="Smith", phone="5551234567"
)

# Update
customer_service.update_customer("cust-123", first_name="Janet")
```

**Model: `Customer`** — flattened from nested API response:

| Field | Type | Source |
|-------|------|--------|
| `.id` | `str \| None` | Top-level `id` |
| `.display_id` | `str \| None` | `displayId` |
| `.first_name` | `str \| None` | `customerDetails.name.firstName` |
| `.last_name` | `str \| None` | `customerDetails.name.lastName` |
| `.phone` | `str \| None` | First `phoneCommunications[].phone.completeNumber` |
| `.email` | `str \| None` | First `emailCommunications[].email` |
| `.customer_type` | `str \| None` | `customerDetails.customerType` |
| `.status` | `str \| None` | Top-level `status` |
| `.vehicles` | `list[Vehicle]` | Top-level `vehicles` |

---

### 2. Vehicle Inventory

**Service:** `tekion_api/services/vehicle.py` — `VehicleService`

| Method | Endpoint | Tier | Description |
|--------|----------|------|-------------|
| `list_all()` | `GET /v4.0.0/vehicle-inventory` | Open | List with filters (vin, make, model, year, status) |
| `search()` | `POST /v4.0.0/vehicle-inventory:search` | Open | Advanced search with operators and pagination |
| `get()` | `GET /v4.0.0/vehicle-inventory/{id}` | Open | Single vehicle detail |
| `update()` | `PUT /v4.0.0/vehicle-inventory/{id}` | Open | Full replacement update |
| `get_repair_orders()` | `GET /v4.0.0/vehicle-inventory/{id}/repair-orders` | Premium | Repair order IDs for this vehicle |

```python
from tekion_api.services.vehicle import VehicleService

# List by VIN
result = vehicle_service.list_all(vin="1FTEW1E45KFA12349")

# Advanced search
result = vehicle_service.search(filters=[{
    "operator": "EQ", "field": "vin", "values": ["1FTEW1E45KFA12349"]
}])

# Get details
vehicle = vehicle_service.get("v-001")

# Get repair history
ros = vehicle_service.get_repair_orders("v-001")
```

---

### 3. Repair Order

**Service:** `tekion_api/services/repair_order.py` — `RepairOrderService`

Covers stages 3 (read), 6 (create), 7 (parts), and 8 (consent) of the workflow.

#### Read / History (Stage 3)

| Method | Endpoint | Tier |
|--------|----------|------|
| `search()` | `POST /v4.0.0/repair-orders:search` | Premium |
| `get()` | `GET /v4.0.0/repair-orders/{id}` | Select |
| `get_customer()` | `GET /v4.0.0/repair-orders/{roId}/ro-customers/{rcId}` | Select |
| `get_vehicle()` | `GET /v4.0.0/repair-orders/{roId}/ro-vehicle` | Select |
| `get_jobs()` | `GET /v4.0.0/repair-orders/{roId}/jobs` | Select |

#### Create (Stage 6)

| Method | Endpoint | Tier |
|--------|----------|------|
| `create()` | `POST /v4.0.0/repair-orders` | Select |
| `create_from_appointment()` | `POST /v4.0.0/repair-orders:appointment-to-ro` | Select |
| `create_job()` | `POST /v4.0.0/repair-orders/{roId}/jobs` | Select |
| `create_operation()` | `POST /v4.0.0/repair-orders/{roId}/jobs/{jobId}/operations` | Select |
| `create_operation_parts()` | `POST .../operations/{opId}/parts` | Select |

#### Parts (Stage 7)

| Method | Endpoint | Tier |
|--------|----------|------|
| `get_part()` | `GET .../operations/{opId}/parts/{partId}` | Select |
| `get_parts()` | `GET .../operations/{opId}/parts` | Select |
| `get_operation_part_fees()` | `GET .../parts/{partId}/part-fees` | Select |

#### Invoices & Status (Stage 8)

| Method | Endpoint | Tier |
|--------|----------|------|
| `get_invoices()` | `GET /v4.0.0/repair-orders/{roId}/ro-invoices` | Premium |
| `get_invoice()` | `GET /v4.0.0/repair-orders/{roId}/ro-invoices/{invId}` | Premium |
| `update_status()` | `PUT /v4.0.0/repair-orders/{id}:status` | Premium |

```python
from tekion_api.services.repair_order import RepairOrderService

# Search for ROs
ros = ro_service.search(filters=[{
    "field": "documentNumber", "operator": "IN", "values": ["5142"]
}])

# Get full RO
ro = ro_service.get("ro-001")

# Get jobs
jobs = ro_service.get_jobs("ro-001")

# Create RO
ro_service.create(
    billing_customer_id="cust-001",
    primary_customer_id="cust-001",
    vin="5J8YD8H87RL004205",
    mileage_in=12345,
)

# Create from appointment
ro_service.create_from_appointment(appointment_id="appt-001")

# Create job
ro_service.create_job("ro-001", concern_text="Oil Leakage", opcode="OIL_CHG",
                       labor_sale_amount=100, bill_duration=2000)

# Add operation
ro_service.create_operation("ro-001", "job-001", opcode="OIL_CHG")

# Add parts
ro_service.create_operation_parts("ro-001", "job-001", "op-001", [{
    "partNumber": "4242342nfn24i52343",
    "unitSaleAmount": 100,
    "partName": "Air Filter",
    "quantities": [{"type": "SALE", "value": 10}],
}])

# Get invoices
invoices = ro_service.get_invoices("ro-001")

# Update status (e.g., void)
ro_service.update_status("ro-001", "VOID", reason="Not required anymore")
```

---

### 4. Support — Transportation

**Service:** `tekion_api/services/support.py` — `SupportService`

| Method | Endpoint | Tier |
|--------|----------|------|
| `get_transportation_types()` | `GET /v4.0.0/transportation-types` | Select |
| `get_transportation_type()` | `GET /v4.0.0/transportation-types/{id}` | Select |

```python
from tekion_api.services.support import SupportService

types = support_service.get_transportation_types()
for t in types.get("data", []):
    print(f"{t['name']} ({t['type']})")

detail = support_service.get_transportation_type("t-001")
```

---

### 5. Service Appointments

**Service:** `tekion_api/services/appointment.py` — `AppointmentService`

| Method | Endpoint | Tier |
|--------|----------|------|
| `search()` | `POST /v4.0.0/service-appointments:search` | Premium |
| `get()` | `GET /v4.0.0/service-appointments/{id}` | Premium |

```python
from tekion_api.services.appointment import AppointmentService

# Search appointments
appointments = appt_service.search(filters=[{
    "field": "status", "operator": "IN", "values": ["NEW", "IN_PROGRESS"]
}])

# Get by ID
appt = appt_service.get("appt-001")
```

---

## Demo Scripts

CLI scripts for quick testing against the Tekion sandbox:

```bash
# Customer operations
uv run python scripts/demo_customer.py search --phone "5551234567"
uv run python scripts/demo_customer.py get --id "cust-123"
uv run python scripts/demo_customer.py create --first "Jane" --last "Smith" --phone "5551234567"

# Vehicle inventory
uv run python scripts/demo_vehicle.py list --vin "1FTEW1E45KFA12349"
uv run python scripts/demo_vehicle.py get --id "v-001"
uv run python scripts/demo_vehicle.py search --make "Ford"
uv run python scripts/demo_vehicle.py repair-orders --id "v-001"

# Repair orders
uv run python scripts/demo_repair_order.py search --doc-number "5142"
uv run python scripts/demo_repair_order.py get --id "ro-001"
uv run python scripts/demo_repair_order.py jobs --ro-id "ro-001"
uv run python scripts/demo_repair_order.py invoices --ro-id "ro-001"

# Support
uv run python scripts/demo_support.py transport-types
uv run python scripts/demo_support.py transport-type --id "t-001"
```

---

## Error Handling

Every API error raises a typed exception:

```python
from tekion_api.exceptions import (
    AuthError,           # Invalid credentials or token
    NotFoundError,       # 404
    RateLimitError,      # 429
    TokenRateLimitError, # Token generation limit (18/15min)
    ValidationError,     # 400/422
    ServerError,         # 5xx
    TekionError,         # Base class
)

try:
    customer = customer_service.get_customer("nonexistent-id")
except NotFoundError:
    print("Customer not found")
except TekionError as e:
    print(f"API error: {e}")
```

---

## Testing

```bash
uv run pytest -v
```

92 tests covering all services — all HTTP calls mocked via `respx`, no network access required.

### Test Breakdown

| Test File | Tests | Covers |
|-----------|-------|--------|
| `tests/test_auth.py` | 6 | Token caching, expiry, refresh, rate limits |
| `tests/test_client.py` | 10 | Headers, 401 retry, error status codes |
| `tests/test_config.py` | 4 | Env var loading, defaults, missing vars |
| `tests/test_exceptions.py` | 6 | Exception hierarchy |
| `tests/test_models.py` | 18 | Customer/Vehicle model parsing |
| `tests/services/test_customer.py` | 10 | Search, get, create, update |
| `tests/services/test_vehicle.py` | 10 | List, search, get, update, repair-orders |
| `tests/services/test_repair_order.py` | 18 | All 14 RO endpoints |
| `tests/services/test_support.py` | 3 | Transportation types |
| `tests/services/test_appointment.py` | 6 | Search, get |

---

## Project Structure

```
tekion_api/
  config.py              # TekionConfig, load_config()
  auth.py                # TokenManager (cache, rate limit, refresh)
  client.py              # ApiClient (HTTP, headers, retry)
  exceptions.py          # 7 typed exceptions
  models/
    common.py            # ApiEnvelope, PaginationMeta
    customer.py          # Vehicle, Customer, CreateCustomerRequest
  services/
    base.py              # ServiceBase
    customer.py          # CustomerService
    vehicle.py           # VehicleService
    repair_order.py      # RepairOrderService (14 methods)
    support.py           # SupportService
    appointment.py       # AppointmentService
scripts/
  demo_customer.py       # Customer CLI
  demo_vehicle.py        # Vehicle CLI
  demo_repair_order.py   # Repair Order CLI
  demo_support.py        # Support CLI
tests/
  conftest.py            # Shared fixtures
  test_auth.py           # TokenManager tests
  test_client.py         # ApiClient tests
  test_config.py         # Config tests
  test_exceptions.py     # Exception tests
  test_models.py         # Model parsing tests
  services/
    test_customer.py     # Customer service tests
    test_vehicle.py      # Vehicle service tests
    test_repair_order.py # Repair Order service tests
    test_support.py      # Support service tests
    test_appointment.py  # Appointment service tests
```

---

## Postman Collection

A complete [Postman collection](tekion-api.postman_collection.json) is included with all endpoints:

- **Auth** — Get Token with auto-save script
- **Customer** — Search, Get by ID, Create, Update
- **Vehicle Inventory** — List, Search, Get, Update, Repair Orders
- **Repair Order** — Search, Get, Customer, Vehicle, Jobs, Create, Invoices, Status
- **Support** — Transportation Types
- **Service Appointments** — Search, Get by ID

Import into Postman, set up environment variables (`app_id`, `secret_key`, `dealer_id`, `base_url`), and start with **Get Token** to authenticate.

---

## Links

- **[GitHub Repository](https://github.com/DanyalAbbas/tekion-api-testing)** — Source code, issues, pull requests
- **[Tekion APC Developer Portal](https://developer.tekion.com)** — API documentation, app registration
- **[Tekion API Sandbox](https://api-sandbox.tekioncloud.com/openapi)** — Sandbox base URL
- **[Tekion Production API](https://api.tekioncloud.com/openapi)** — Production base URL
- **[Postman Collection](tekion-api.postman_collection.json)** — Pre-built API requests
- **[AutoAdvisor AI](https://github.com/DanyalAbbas/tekion-api-testing)** — Voice agent for dealership service
