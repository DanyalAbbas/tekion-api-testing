import respx
import pytest

from tekion_api.client import ApiClient


TRANSPORT_TYPES_RESPONSE = {
    "data": [
        {"id": "t-001", "name": "Loaner Car", "type": "LOANER"},
        {"id": "t-002", "name": "Shuttle", "type": "SHUTTLE"},
    ]
}

TRANSPORT_TYPE_RESPONSE = {
    "data": {
        "id": "t-001",
        "name": "Loaner Car",
        "type": "LOANER",
        "description": "Courtesy loaner vehicle",
    }
}


@pytest.fixture
def _dummy_tm():
    class _Dummy:
        def get_token(self):
            return "test-token"
    return _Dummy()


@pytest.fixture
def support_service(sandbox_config, _dummy_tm):
    client = ApiClient(sandbox_config, token_manager=_dummy_tm)
    from tekion_api.services.support import SupportService
    return SupportService(client)


class TestSupportService:
    def test_get_transportation_types(self, support_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/transportation-types"
        ).respond(200, json=TRANSPORT_TYPES_RESPONSE)

        result = support_service.get_transportation_types()
        assert len(result["data"]) == 2
        assert result["data"][0]["type"] == "LOANER"
        assert route.called

    def test_get_transportation_type(self, support_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/transportation-types/t-001"
        ).respond(200, json=TRANSPORT_TYPE_RESPONSE)

        result = support_service.get_transportation_type("t-001")
        assert result["data"]["name"] == "Loaner Car"
        assert route.called

    def test_get_transportation_type_not_found(self, support_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/transportation-types/missing"
        ).respond(404, json={"status": "error"})

        from tekion_api.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            support_service.get_transportation_type("missing")
        assert route.called
