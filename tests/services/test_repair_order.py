import respx
import pytest

from tekion_api.client import ApiClient


RO_SEARCH_RESPONSE = {
    "meta": {"totalCount": 1},
    "data": [{"id": "ro-001", "documentNumber": "5142", "status": "OPEN"}],
}

RO_RESPONSE = {
    "data": {
        "id": "ro-001",
        "documentNumber": "5142",
        "status": "OPEN",
        "customerId": "cust-001",
        "vehicleId": "v-001",
    }
}

RO_CUSTOMER_RESPONSE = {
    "data": {
        "id": "rc-001",
        "firstName": "John",
        "lastName": "Doe",
        "phone": "+15550100",
    }
}

RO_VEHICLE_RESPONSE = {
    "data": {
        "id": "v-001",
        "vin": "1FTEW1E45KFA12349",
        "year": "2024",
        "make": "Ford",
        "model": "F-150",
    }
}

RO_JOBS_RESPONSE = {
    "data": [
        {"id": "job-001", "taskCode": "OIL_CHG", "description": "Oil Change", "status": "OPEN"},
        {"id": "job-002", "taskCode": "TIRE_ROT", "description": "Tire Rotation", "status": "OPEN"},
    ]
}


@pytest.fixture
def _dummy_tm():
    class _Dummy:
        def get_token(self):
            return "test-token"
    return _Dummy()


@pytest.fixture
def ro_service(sandbox_config, _dummy_tm):
    client = ApiClient(sandbox_config, token_manager=_dummy_tm)
    from tekion_api.services.repair_order import RepairOrderService
    return RepairOrderService(client)


class TestRepairOrderService:
    def test_search(self, ro_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders:search"
        ).respond(200, json=RO_SEARCH_RESPONSE)

        filters = [{"field": "documentNumber", "operator": "IN", "values": ["5142"]}]
        result = ro_service.search(filters=filters)
        assert result["data"][0]["documentNumber"] == "5142"
        assert route.called

    def test_search_with_pagination(self, ro_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders:search"
        ).respond(200, json={"meta": {}, "data": []})

        result = ro_service.search(pagination_token="token123", page_size=50)
        assert route.called
        body = route.calls[0].request.content
        assert b"token123" in body
        assert b"50" in body

    def test_get(self, ro_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001"
        ).respond(200, json=RO_RESPONSE)

        result = ro_service.get("ro-001")
        assert result["data"]["id"] == "ro-001"
        assert route.called

    def test_get_not_found(self, ro_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/missing"
        ).respond(404, json={"status": "error"})

        from tekion_api.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            ro_service.get("missing")
        assert route.called

    def test_get_customer(self, ro_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/ro-customers/rc-001"
        ).respond(200, json=RO_CUSTOMER_RESPONSE)

        result = ro_service.get_customer("ro-001", "rc-001")
        assert result["data"]["firstName"] == "John"
        assert route.called

    def test_get_vehicle(self, ro_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/ro-vehicle"
        ).respond(200, json=RO_VEHICLE_RESPONSE)

        result = ro_service.get_vehicle("ro-001")
        assert result["data"]["vin"] == "1FTEW1E45KFA12349"
        assert route.called

    def test_get_jobs(self, ro_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/jobs"
        ).respond(200, json=RO_JOBS_RESPONSE)

        result = ro_service.get_jobs("ro-001")
        assert len(result["data"]) == 2
        assert result["data"][0]["taskCode"] == "OIL_CHG"
        assert route.called

    def test_create(self, ro_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders"
        ).respond(201, json={"data": {"id": "ro-001", "documentNumber": "5142"}})

        result = ro_service.create(
            billing_customer_id="cust-001",
            primary_customer_id="cust-001",
            vin="5J8YD8H87RL004205",
            mileage_in=12345,
            license_plate="TT-123-TT",
            tag_number="12345",
        )
        assert result["data"]["id"] == "ro-001"
        assert route.called

    def test_create_from_appointment(self, ro_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders:appointment-to-ro"
        ).respond(201, json={"data": {"id": "ro-001"}})

        result = ro_service.create_from_appointment(
            appointment_id="appt-001",
            tag_number="6254324",
        )
        assert result["data"]["id"] == "ro-001"
        assert route.called

    def test_create_job(self, ro_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/jobs"
        ).respond(201, json={"data": {"id": "job-001"}})

        result = ro_service.create_job(
            ro_id="ro-001",
            concern_text="Oil Leakage",
            opcode="OIL_CHG",
            opcode_description="Oil Change",
            labor_sale_amount=100,
            bill_duration=2000,
        )
        assert result["data"]["id"] == "job-001"
        assert route.called

    def test_create_operation(self, ro_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/jobs/job-001/operations"
        ).respond(201, json={"data": {"id": "op-001"}})

        result = ro_service.create_operation(
            ro_id="ro-001", job_id="job-001",
            opcode="OIL_CHG",
            labor_sale_amount=100,
            bill_duration=2000,
        )
        assert result["data"]["id"] == "op-001"
        assert route.called

    def test_create_operation_parts(self, ro_service, respx_mock):
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/jobs/job-001/operations/op-001/parts"
        ).respond(201, json={"data": [{"id": "part-001"}]})

        parts = [{
            "partNumber": "4242342nfn24i52343",
            "unitSaleAmount": 100,
            "partName": "Air Filter",
            "quantities": [{"type": "SALE", "value": 10}],
        }]
        result = ro_service.create_operation_parts("ro-001", "job-001", "op-001", parts)
        assert result["data"][0]["id"] == "part-001"
        assert route.called

    def test_get_part(self, ro_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/jobs/job-001/operations/op-001/parts/part-001"
        ).respond(200, json={"data": {"id": "part-001", "partName": "Air Filter"}})

        result = ro_service.get_part("ro-001", "job-001", "op-001", "part-001")
        assert result["data"]["partName"] == "Air Filter"
        assert route.called

    def test_get_parts(self, ro_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/jobs/job-001/operations/op-001/parts"
        ).respond(200, json={"data": [{"id": "part-001"}, {"id": "part-002"}]})

        result = ro_service.get_parts("ro-001", "job-001", "op-001")
        assert len(result["data"]) == 2
        assert route.called

    def test_get_operation_part_fees(self, ro_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/jobs/job-001/operations/op-001/parts/part-001/part-fees"
        ).respond(200, json={"data": [{"feeType": "ENV", "amount": 5}]})

        result = ro_service.get_operation_part_fees("ro-001", "job-001", "op-001", "part-001")
        assert result["data"][0]["feeType"] == "ENV"
        assert route.called

    def test_get_invoices(self, ro_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/ro-invoices"
        ).respond(200, json={"data": [{"id": "inv-001"}, {"id": "inv-002"}]})

        result = ro_service.get_invoices("ro-001")
        assert len(result["data"]) == 2
        assert route.called

    def test_get_invoice(self, ro_service, respx_mock):
        route = respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001/ro-invoices/inv-001"
        ).respond(200, json={"data": {"id": "inv-001", "totalAmount": 250.0}})

        result = ro_service.get_invoice("ro-001", "inv-001")
        assert result["data"]["totalAmount"] == 250.0
        assert route.called

    def test_update_status(self, ro_service, respx_mock):
        route = respx_mock.put(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/repair-orders/ro-001:status"
        ).respond(200, json={"data": {"id": "ro-001", "status": "VOID"}})

        result = ro_service.update_status("ro-001", "VOID", reason="Not required anymore")
        assert result["data"]["status"] == "VOID"
        assert route.called
