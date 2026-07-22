import respx
import pytest

from tekion_api.client import ApiClient


APPT_SEARCH_RESPONSE = {
    "meta": {"totalCount": 1},
    "data": [{
        "id": "appt-001",
        "appointmentDateTime": 1768300800000,
        "status": "NEW",
        "customerId": "cust-001",
    }],
}

APPT_RESPONSE = {
    "data": {
        "id": "appt-001",
        "appointmentDateTime": 1768300800000,
        "status": "NEW",
        "customerId": "cust-001",
        "vehicleId": "v-001",
    }
}


@pytest.fixture
def _dummy_tm():
    class _Dummy:
        def get_token(self):
            return "test-token"
    return _Dummy()


@pytest.fixture
def appt_service(sandbox_config, _dummy_tm):
    client = ApiClient(sandbox_config, token_manager=_dummy_tm)
    from tekion_api.services.appointment import AppointmentService
    return AppointmentService(client)


class TestAppointmentService:
    def test_search(self, appt_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/service-appointments:search"
        ).respond(200, json=APPT_SEARCH_RESPONSE)

        filters = [{"field": "status", "operator": "IN", "values": ["NEW"]}]
        result = appt_service.search(filters=filters)
        assert result["data"][0]["status"] == "NEW"
        assert route.called

    def test_search_with_text(self, appt_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/service-appointments:search"
        ).respond(200, json=APPT_SEARCH_RESPONSE)

        result = appt_service.search(text_search="11261")
        assert route.called
        body = route.calls[0].request.content
        assert b"11261" in body

    def test_search_with_sort(self, appt_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/service-appointments:search"
        ).respond(200, json=APPT_SEARCH_RESPONSE)

        sort = [{"field": "appointmentDateTime", "order": "DESC"}]
        result = appt_service.search(sort=sort)
        assert route.called

    def test_search_with_pagination(self, appt_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/service-appointments:search"
        ).respond(200, json={"meta": {}, "data": []})

        result = appt_service.search(pagination_token="tok_123", page_size=50)
        assert route.called
        body = route.calls[0].request.content
        assert b"tok_123" in body

    def test_get(self, appt_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/service-appointments/appt-001"
        ).respond(200, json=APPT_RESPONSE)

        result = appt_service.get("appt-001")
        assert result["data"]["id"] == "appt-001"
        assert result["data"]["status"] == "NEW"
        assert route.called

    def test_get_not_found(self, appt_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/service-appointments/missing"
        ).respond(404, json={"status": "error"})

        from tekion_api.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            appt_service.get("missing")
        assert route.called
