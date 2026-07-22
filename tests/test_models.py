import json
import pytest
from pydantic import ValidationError

from tekion_api.models.common import ApiEnvelope
from tekion_api.models.customer import Customer, CreateCustomerRequest


class TestApiEnvelope:
    def test_status_data_pattern(self):
        """Handle {status, data} envelope from auth endpoints."""
        env = ApiEnvelope.model_validate({
            "status": "success",
            "data": {"token": "abc", "expire_on": 12345},
        })
        assert env.status == "success"
        assert env.data["token"] == "abc"

    def test_meta_data_pattern(self):
        """Handle {meta, data} envelope from resource endpoints."""
        env = ApiEnvelope.model_validate({
            "meta": {"nextFetchKey": "abc123"},
            "data": [{"id": "1"}, {"id": "2"}],
        })
        assert env.meta["nextFetchKey"] == "abc123"
        assert len(env.data) == 2

    def test_extra_fields_ignored(self):
        """Future unknown fields do NOT cause validation errors."""
        env = ApiEnvelope.model_validate({
            "status": "success",
            "data": {},
            "newFutureField": "someValue",
            "anotherFutureField": {"nested": 1},
        })
        assert env.status == "success"


class TestCustomer:
    def test_minimal_customer(self):
        """Customer extracts fields from nested structure."""
        c = Customer.model_validate({
            "id": "cust-123",
            "customerDetails": {
                "name": {"firstName": "John", "lastName": "Doe"},
            },
        })
        assert c.id == "cust-123"
        assert c.first_name == "John"
        assert c.last_name == "Doe"

    def test_customer_from_real_response(self):
        """Real Tekion API response structure is parsed correctly."""
        c = Customer.model_validate({
            "id": "cust-001",
            "displayId": "411742",
            "customerDetails": {
                "phoneCommunications": [
                    {"phone": {"completeNumber": "+15551234567", "localNumber": "5551234567"}}
                ],
                "emailCommunications": [
                    {"email": "john@example.com"}
                ],
                "customerType": "INDIVIDUAL",
                "name": {"firstName": "John", "lastName": "Doe"},
            },
            "status": "ACTIVE",
        })
        assert c.id == "cust-001"
        assert c.display_id == "411742"
        assert c.first_name == "John"
        assert c.last_name == "Doe"
        assert c.phone == "+15551234567"
        assert c.email == "john@example.com"
        assert c.customer_type == "INDIVIDUAL"
        assert c.status == "ACTIVE"

    def test_customer_unknown_fields_ignored(self):
        """Extra fields in the response are silently ignored."""
        c = Customer.model_validate({
            "id": "cust-1",
            "customerDetails": {"name": {"firstName": "Jane"}},
            "someNewTekionField": "should-not-break",
        })
        assert c.id == "cust-1"
        assert c.first_name == "Jane"

    def test_customer_missing_customer_details(self):
        """Customer with no customerDetails still parses."""
        c = Customer.model_validate({"id": "cust-1"})
        assert c.id == "cust-1"
        assert c.first_name is None

    def test_customer_empty_id(self):
        """Customer with no ID is still parseable."""
        c = Customer.model_validate({"customerDetails": {}})
        assert c.id is None

    def test_name_with_phone_and_email(self):
        """Extracts phone and email from communications arrays."""
        c = Customer.model_validate({
            "customerDetails": {
                "phoneCommunications": [
                    {"phone": {"completeNumber": "+15555550100"}}
                ],
                "emailCommunications": [
                    {"email": "alice@example.com"}
                ],
                "name": {"firstName": "Alice", "lastName": "Smith"},
            }
        })
        assert c.first_name == "Alice"
        assert c.last_name == "Smith"
        assert c.phone == "+15555550100"
        assert c.email == "alice@example.com"

    def test_phone_falls_back_to_local_number(self):
        """When completeNumber is absent, uses localNumber."""
        c = Customer.model_validate({
            "customerDetails": {
                "phoneCommunications": [
                    {"phone": {"localNumber": "555-0100"}}
                ],
            }
        })
        assert c.phone == "555-0100"

    def test_customer_with_vehicles(self):
        """Vehicles are parsed from the top-level array."""
        c = Customer.model_validate({
            "id": "cust-1",
            "vehicles": [
                {
                    "vin": "1FTEW1E45KFA12349",
                    "year": "2024",
                    "make": "Ford",
                    "model": "F-150",
                    "vehicleId": "v-001",
                    "last8DigitVIN": "KFA12349",
                },
                {
                    "vin": "3GTU2NEC7HG502779",
                    "year": "2017",
                    "make": "GMC",
                    "model": "Sierra 1500",
                    "vehicleId": "v-002",
                    "last8DigitVIN": "HG502779",
                },
            ],
            "customerDetails": {"name": {"firstName": "John"}},
        })
        assert len(c.vehicles) == 2
        assert c.vehicles[0].vin == "1FTEW1E45KFA12349"
        assert c.vehicles[0].make == "Ford"
        assert c.vehicles[0].model == "F-150"
        assert c.vehicles[0].year == "2024"
        assert c.vehicles[0].vehicle_id == "v-001"
        assert c.vehicles[0].last8_digit_vin == "KFA12349"
        assert c.vehicles[1].vin == "3GTU2NEC7HG502779"

    def test_customer_no_vehicles(self):
        """Customer without vehicles gets empty list."""
        c = Customer.model_validate({
            "id": "cust-2",
            "customerDetails": {"name": {"firstName": "Jane"}},
        })
        assert c.vehicles == []

    def test_vehicle_unknown_fields_ignored(self):
        """Extra fields on a vehicle are silently ignored."""
        from tekion_api.models.customer import Vehicle
        v = Vehicle.model_validate({
            "vin": "ABC123",
            "make": "Toyota",
            "someFutureField": "should-not-break",
        })
        assert v.vin == "ABC123"
        assert v.make == "Toyota"


class TestCreateCustomerRequest:
    def test_minimal_payload(self):
        """CreateCustomerRequest produces the minimal nested JSON."""
        req = CreateCustomerRequest(
            first_name="John",
            last_name="Doe",
            phone="5551234567",
            country_code=1,
        )
        payload = req.to_dict()

        assert payload["status"] == "ACTIVE"
        assert payload["customerDetails"]["customerType"] == "INDIVIDUAL"
        assert payload["customerDetails"]["name"]["firstName"] == "John"
        assert payload["customerDetails"]["name"]["lastName"] == "Doe"
        assert payload["customerDetails"]["phoneCommunications"][0]["phone"]["countryCode"] == 1
        assert payload["customerDetails"]["phoneCommunications"][0]["phone"]["localNumber"] == "5551234567"

    def test_payload_is_serializable(self):
        """to_dict() returns JSON-serializable dict (no Pydantic models)."""
        req = CreateCustomerRequest(
            first_name="Jane",
            last_name="Smith",
            phone="555-9876",
        )
        payload = req.to_dict()
        # Should not raise
        json.dumps(payload)

    def test_requires_first_name(self):
        """first_name is required."""
        with pytest.raises(ValidationError):
            CreateCustomerRequest(last_name="Smith", phone="555-0000")

    def test_requires_last_name(self):
        """last_name is required."""
        with pytest.raises(ValidationError):
            CreateCustomerRequest(first_name="John", phone="555-0000")

    def test_requires_phone(self):
        """phone is required."""
        with pytest.raises(ValidationError):
            CreateCustomerRequest(first_name="John", last_name="Doe")
