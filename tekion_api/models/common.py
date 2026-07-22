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
