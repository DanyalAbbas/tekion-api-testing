import respx
import pytest

from tekion_api.services.customer import CustomerService
from tekion_api.models.customer import Customer
from tekion_api.exceptions import NotFoundError, ValidationError


CUSTOMER_SEARCH_RESPONSE = {
    "meta": {"nextFetchKey": None},
    "data": [
        {
            "id": "cust-001",
            "customerDetails": {
                "name": {"firstName": "John", "lastName": "Doe"},
                "phoneCommunications": [{"phone": {"completeNumber": "+15550100"}}],
                "emailCommunications": [{"email": "john@example.com"}],
            },
        },
        {
            "id": "cust-002",
            "customerDetails": {
                "name": {"firstName": "Jane", "lastName": "Smith"},
                "phoneCommunications": [{"phone": {"completeNumber": "+15550200"}}],
                "emailCommunications": [{"email": "jane@example.com"}],
            },
        },
    ],
}

SINGLE_CUSTOMER_RESPONSE = {
    "data": {
        "id": "cust-001",
        "customerDetails": {
            "name": {"firstName": "John", "lastName": "Doe"},
            "phoneCommunications": [{"phone": {"completeNumber": "+15550100"}}],
            "emailCommunications": [{"email": "john@example.com"}],
            "customerType": "INDIVIDUAL",
        },
        "status": "ACTIVE",
    }
}


@pytest.fixture
def _dummy_token_manager():
    class _Dummy:
        def get_token(self):
            return "test-token"
    return _Dummy()


@pytest.fixture
def customer_service(sandbox_config, _dummy_token_manager):
    from tekion_api.client import ApiClient
    client = ApiClient(sandbox_config, token_manager=_dummy_token_manager)
    return CustomerService(client)


class TestCustomerService:
    def test_search_by_phone_found(self, customer_service, respx_mock):
        """search_customers returns list of Customer objects."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers?phone=555-0100"
        ).respond(200, json=CUSTOMER_SEARCH_RESPONSE)

        results = customer_service.search_customers(phone="555-0100")

        assert len(results) == 2
        assert results[0].id == "cust-001"
        assert results[0].first_name == "John"
        assert results[1].id == "cust-002"

    def test_search_by_phone_not_found(self, customer_service, respx_mock):
        """search_customers returns empty list when no match."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers?phone=555-9999"
        ).respond(200, json={"meta": {}, "data": []})

        results = customer_service.search_customers(phone="555-9999")
        assert results == []

    def test_search_by_phone_with_name(self, customer_service, respx_mock):
        """Search can combine phone and name filters."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
            "?phone=555-0100&firstName=John"
        ).respond(200, json={"meta": {}, "data": [CUSTOMER_SEARCH_RESPONSE["data"][0]]})

        results = customer_service.search_customers(phone="555-0100", first_name="John")
        assert len(results) == 1
        assert results[0].first_name == "John"

    def test_search_by_email(self, customer_service, respx_mock):
        """Search can use email filter."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
            "?email=john@example.com"
        ).respond(200, json={"meta": {}, "data": [CUSTOMER_SEARCH_RESPONSE["data"][0]]})

        results = customer_service.search_customers(email="john@example.com")
        assert len(results) == 1

    def test_search_with_general_term(self, customer_service, respx_mock):
        """Search can use the general 'search' parameter."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
            "?search=John+Doe"
        ).respond(200, json={"meta": {}, "data": [CUSTOMER_SEARCH_RESPONSE["data"][0]]})

        results = customer_service.search_customers(search="John Doe")
        assert len(results) == 1

    def test_get_customer_found(self, customer_service, respx_mock):
        """get_customer returns a single Customer by ID."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-001"
        ).respond(200, json=SINGLE_CUSTOMER_RESPONSE)

        customer = customer_service.get_customer("cust-001")
        assert customer.id == "cust-001"
        assert customer.first_name == "John"

    def test_get_customer_not_found(self, customer_service, respx_mock):
        """get_customer raises NotFoundError for missing ID."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/missing-id"
        ).respond(404, json={"status": "error"})

        with pytest.raises(NotFoundError):
            customer_service.get_customer("missing-id")

    def test_create_customer_minimal(self, customer_service, respx_mock):
        """create_customer returns the created customer."""
        route = respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
        ).respond(201, json=SINGLE_CUSTOMER_RESPONSE)

        customer = customer_service.create_customer(
            first_name="John",
            last_name="Doe",
            phone="555-0100",
        )
        assert customer.id == "cust-001"
        assert customer.first_name == "John"
        assert route.called

    def test_create_customer_invalid(self, customer_service, respx_mock):
        """create_customer raises ValidationError on bad data."""
        respx_mock.post(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers"
        ).respond(400, json={"status": "error", "data": {"message": "Invalid phone number"}})

        with pytest.raises(ValidationError, match="Invalid phone number"):
            customer_service.create_customer(
                first_name="John",
                last_name="Doe",
                phone="not-a-phone",
            )

    def test_update_customer(self, customer_service, respx_mock):
        """update_customer sends PUT and returns updated Customer."""
        # update_customer reads current data first, then PUTs the update
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-001"
        ).respond(200, json=SINGLE_CUSTOMER_RESPONSE)

        updated_response = {
            "data": {
                **SINGLE_CUSTOMER_RESPONSE["data"],
                "customerDetails": {
                    **SINGLE_CUSTOMER_RESPONSE["data"]["customerDetails"],
                    "name": {"firstName": "Jonathan", "lastName": "Doe"},
                },
            }
        }
        route = respx_mock.put(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/cust-001"
        ).respond(200, json=updated_response)

        customer = customer_service.update_customer(
            "cust-001",
            first_name="Jonathan",
            last_name="Doe",
            phone="555-0100",
        )
        assert customer.first_name == "Jonathan"
        assert route.called

    def test_update_customer_not_found(self, customer_service, respx_mock):
        """update_customer raises NotFoundError for missing ID."""
        respx_mock.get(
            "https://api-sandbox.tekioncloud.com/openapi/v4.0.0/customers/missing"
        ).respond(404, json={"status": "error"})

        with pytest.raises(NotFoundError):
            customer_service.update_customer(
                "missing",
                first_name="No",
                last_name="One",
                phone="555-0000",
            )
