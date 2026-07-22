import respx
import pytest

from tekion_api.client import ApiClient


SEARCH_RESPONSE = {
    "meta": {"nextFetchToken": None, "totalCount": 1},
    "data": [{
        "id": "v-001",
        "vin": "1FTEW1E45KFA12349",
        "year": "2024",
        "make": "Ford",
        "model": "F-150",
    }],
}

VEHICLE_RESPONSE = {
    "data": {
        "id": "v-001",
        "vin": "1FTEW1E45KFA12349",
        "year": "2024",
        "make": "Ford",
        "model": "F-150",
        "status": "STOCKED_IN",
    }
}


@pytest.fixture
def _dummy_tm():
    class _Dummy:
        def get_token(self):
            return "test-token"
    return _Dummy()


@pytest.fixture
def vehicle_service(sandbox_config, _dummy_tm):
    client = ApiClient(sandbox_config, token_manager=_dummy_tm)
    from tekion_api.services.vehicle import VehicleService
    return VehicleService(client)


class TestVehicleService:
    def test_list_all(self, vehicle_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/vehicle-inventory"
        ).respond(200, json={"data": [{"id": "v-001"}, {"id": "v-002"}]})

        result = vehicle_service.list_all()
        assert len(result["data"]) == 2
        assert route.called

    def test_list_all_with_filters(self, vehicle_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/vehicle-inventory?make=Honda&year=2022"
        ).respond(200, json={"data": []})

        result = vehicle_service.list_all(make="Honda", year="2022")
        assert result["data"] == []
        assert route.called

    def test_list_all_by_vin(self, vehicle_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/vehicle-inventory?vin=1FTEW1E45KFA12349"
        ).respond(200, json={"data": [{"id": "v-001", "vin": "1FTEW1E45KFA12349"}]})

        result = vehicle_service.list_all(vin="1FTEW1E45KFA12349")
        assert result["data"][0]["vin"] == "1FTEW1E45KFA12349"
        assert route.called

    def test_search_by_vin(self, vehicle_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/vehicle-inventory:search"
        ).respond(200, json=SEARCH_RESPONSE)

        result = vehicle_service.search(vin="1FTEW1E45KFA12349")
        assert result["data"][0]["vin"] == "1FTEW1E45KFA12349"
        assert route.called

    def test_search_with_custom_filters(self, vehicle_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/vehicle-inventory:search"
        ).respond(200, json=SEARCH_RESPONSE)

        filters = [{"operator": "EQ", "field": "make", "values": ["Ford"]}]
        result = vehicle_service.search(filters=filters)
        assert result["data"][0]["make"] == "Ford"
        assert route.called

    def test_search_with_pagination(self, vehicle_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/vehicle-inventory:search"
        ).respond(200, json={"meta": {}, "data": []})

        result = vehicle_service.search(pagination_token="abc123", page_size=50)
        assert route.called
        body = route.calls[0].request.content
        assert b"abc123" in body
        assert b"50" in body

    def test_get_vehicle(self, vehicle_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/vehicle-inventory/v-001"
        ).respond(200, json=VEHICLE_RESPONSE)

        result = vehicle_service.get("v-001")
        assert result["data"]["id"] == "v-001"
        assert result["data"]["vin"] == "1FTEW1E45KFA12349"
        assert route.called

    def test_update_vehicle(self, vehicle_service, respx_mock):
        route = respx_mock.put(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/vehicle-inventory/v-001"
        ).respond(200, json=VEHICLE_RESPONSE)

        payload = {"odometerReading": {"value": 15000, "status": "ACTUAL"}}
        result = vehicle_service.update("v-001", payload)
        assert result["data"]["id"] == "v-001"
        assert route.called

    def test_get_repair_orders(self, vehicle_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/vehicle-inventory/v-001/repair-orders"
        ).respond(200, json={"data": ["ro-001", "ro-002"]})

        result = vehicle_service.get_repair_orders("v-001")
        assert "ro-001" in result["data"]
        assert route.called

    def test_get_repair_orders_not_found(self, vehicle_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/vehicle-inventory/missing/repair-orders"
        ).respond(404, json={"status": "error"})

        from tekion_api.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            vehicle_service.get_repair_orders("missing")
        assert route.called
