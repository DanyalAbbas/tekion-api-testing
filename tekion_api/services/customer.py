import logging

from tekion_api.client import ApiClient
from tekion_api.models.customer import Customer, CreateCustomerRequest
from tekion_api.services.base import ServiceBase

logger = logging.getLogger(__name__)

CUSTOMER_PATH = "/v4.0.0/customers"


class CustomerService(ServiceBase):
    """Domain service for Tekion Customer operations.

    Every method maps to one API endpoint call. No orchestration logic.
    The caller decides how to sequence calls (search → create, etc.).
    """

    def __init__(self, client: ApiClient):
        super().__init__(client)

    def search_customers(
        self,
        *,
        phone: str | None = None,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        search: str | None = None,
        customer_type: str | None = None,
        **extra_params,
    ) -> list[Customer]:
        """Search customers by phone, email, name, or general search term.

        PREMIUM tier API. Returns list of matching customers (may be empty).
        """
        params = {}
        if phone is not None:
            params["phone"] = phone
        if email is not None:
            params["email"] = email
        if first_name is not None:
            params["firstName"] = first_name
        if last_name is not None:
            params["lastName"] = last_name
        if search is not None:
            params["search"] = search
        if customer_type is not None:
            params["customerType"] = customer_type
        # Allow extra filters like id, companyName, nextFetchKey
        params.update(extra_params)

        logger.info("Searching customers with filters: %s", {k: v for k, v in params.items() if k != "phone"})
        response = self._client.get(CUSTOMER_PATH, params=params)

        raw_data = response.get("data", [])
        if not raw_data:
            return []
        return [Customer.model_validate(c) for c in raw_data]

    def get_customer(self, customer_id: str) -> Customer:
        """Fetch a single customer by their Tekion customer ID.

        SELECT tier API. Raises NotFoundError if the ID doesn't exist.
        """
        logger.info("Fetching customer: %s", customer_id)
        response = self._client.get(f"{CUSTOMER_PATH}/{customer_id}")
        raw_data = response.get("data", {})
        return Customer.model_validate(raw_data)

    def create_customer(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        country_code: int = 1,
    ) -> Customer:
        """Create a new customer with minimal required fields.

        OPEN tier API. Returns the created Customer with assigned ID.
        """
        req = CreateCustomerRequest(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            country_code=country_code,
        )
        payload = req.to_dict()
        logger.info("Creating customer: %s %s", first_name, last_name)
        response = self._client.post(CUSTOMER_PATH, json=payload)
        raw_data = response.get("data", {})
        return Customer.model_validate(raw_data)

    def update_customer(
        self,
        customer_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        phone: str | None = None,
        country_code: int = 1,
    ) -> Customer:
        """Update an existing customer's details.

        OPEN tier API. Only provided fields are sent; omitted fields
        retain their existing values on the server.
        """
        current_data = self.get_customer(customer_id)

        req = CreateCustomerRequest(
            first_name=first_name or current_data.first_name or "",
            last_name=last_name or current_data.last_name or "",
            phone=phone or current_data.phone or "",
            country_code=country_code,
        )
        payload = req.to_dict()
        logger.info("Updating customer: %s", customer_id)
        response = self._client.put(f"{CUSTOMER_PATH}/{customer_id}", json=payload)
        raw_data = response.get("data", {})
        return Customer.model_validate(raw_data)
