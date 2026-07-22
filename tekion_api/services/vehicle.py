import logging

from tekion_api.client import ApiClient
from tekion_api.services.base import ServiceBase

logger = logging.getLogger(__name__)

VEHICLE_PATH = "/v4.0.0/vehicle-inventory"


class VehicleService(ServiceBase):
    def __init__(self, client: ApiClient):
        super().__init__(client)

    def list_all(self, **params) -> dict:
        return self._client.get(VEHICLE_PATH, params=params or None)

    def search(self, *, vin: str | None = None, pagination_token: str | None = None,
               page_size: int = 20, filters: list[dict] | None = None, **extra) -> dict:
        params = {}
        body: dict[str, object] = {"pageSize": page_size}
        if pagination_token:
            body["paginationToken"] = pagination_token
        if filters:
            body["filters"] = filters
        elif vin:
            body["filters"] = [{
                "operator": "EQ",
                "field": "vin",
                "values": [vin],
            }]
        if extra:
            body.setdefault("filters", []).extend(extra.get("extra_filters", []))
        return self._client.post(f"{VEHICLE_PATH}:search", json=body)

    def get(self, vehicle_inventory_id: str) -> dict:
        return self._client.get(f"{VEHICLE_PATH}/{vehicle_inventory_id}")

    def update(self, vehicle_inventory_id: str, payload: dict) -> dict:
        return self._client.put(f"{VEHICLE_PATH}/{vehicle_inventory_id}", json=payload)

    def get_repair_orders(self, vehicle_inventory_id: str) -> dict:
        return self._client.get(f"{VEHICLE_PATH}/{vehicle_inventory_id}/repair-orders")
