import respx
import pytest

from tekion_api.client import ApiClient


CUSTOMER = {
    "id": "cust-001", "firstName": "Ashu", "lastName": "Arora",
    "phones": [{"phoneType": "MOBILE", "number": "0007795962", "isPrimary": True}],
    "email": "ashu@example.com",
}
VEHICLE = {"id": "v-001", "vin": "3GTU2NEC7HG502779", "year": 2017, "make": "GMC", "model": "Sierra 1500"}

SLOTS_RESPONSE = {"data": [{"startTime": "2024-01-26T09:00:00Z", "endTime": "2024-01-26T09:30:00Z"}]}
SEARCH_RESPONSE = {"data": [{"id": "appt-001", "customer": CUSTOMER, "vehicle": VEHICLE}]}
CREATE_RESPONSE = {"data": {"id": "appt-001"}}
UPDATE_RESPONSE = {"data": {"id": "appt-001", "status": "UPDATED"}}
CANCEL_RESPONSE = {"data": {"id": "appt-001", "status": "CANCELLED"}}


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
    def test_get_slots(self, appt_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v3.1.0/appointment-slots"
        ).respond(200, json=SLOTS_RESPONSE)

        result = appt_service.get_slots(
            shop_id="shop-001", start_date="2024-01-26", end_date="2024-01-31",
            year=2017, make="GMC", model="Sierra 1500",
            opcodes=["MPI"],
        )
        assert len(result["data"]) > 0
        assert route.called
        body = route.calls[0].request.content
        assert b"shop-001" in body
        assert b"MPI" in body

    def test_search_by_id(self, appt_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v3.1.0/appointments?id=appt-001"
        ).respond(200, json=SEARCH_RESPONSE)

        result = appt_service.search(appointment_id="appt-001")
        assert result["data"][0]["id"] == "appt-001"
        assert route.called

    def test_search_by_vin(self, appt_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v3.1.0/appointments?vin=3GTU2NEC7HG502779"
        ).respond(200, json=SEARCH_RESPONSE)

        result = appt_service.search(vin="3GTU2NEC7HG502779")
        assert result["data"][0]["vehicle"]["vin"] == "3GTU2NEC7HG502779"
        assert route.called

    def test_search_with_pagination(self, appt_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v3.1.0/appointments?nextFetchKey=token123"
        ).respond(200, json={"data": []})

        result = appt_service.search(next_fetch_key="token123")
        assert route.called

    def test_create(self, appt_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v3.1.0/appointments"
        ).respond(201, json=CREATE_RESPONSE)

        result = appt_service.create(
            shop_id="shop-001",
            appointment_date_time=1644073200000,
            customer=CUSTOMER,
            vehicle=VEHICLE,
            transportation_type_id="trans-001",
            service_advisor_id="TEK00",
            jobs=[{"type": "DEFAULT", "payType": "CUSTOMER_PAY", "concern": "Minor", "operations": []}],
        )
        assert result["data"]["id"] == "appt-001"
        assert route.called
        body = route.calls[0].request.content
        assert b"shop-001" in body

    def test_update(self, appt_service, respx_mock):
        route = respx_mock.put(
            "https://api-sandbox.tekioncloud.com/openapi/v3.1.0/appointments"
        ).respond(200, json=UPDATE_RESPONSE)

        result = appt_service.update(
            id="appt-001", shop_id="shop-001",
            appointment_date_time=1644073200000,
            customer=CUSTOMER, vehicle=VEHICLE,
            customer_comments="Updated request",
        )
        assert result["data"]["status"] == "UPDATED"
        assert route.called

    def test_cancel(self, appt_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v3.1.0/appointments/cancel"
        ).respond(200, json=CANCEL_RESPONSE)

        result = appt_service.cancel("appt-001", cancel_reason="Customer requested rescheduling")
        assert result["data"]["status"] == "CANCELLED"
        assert route.called
        body = route.calls[0].request.content
        assert b"rescheduling" in body
