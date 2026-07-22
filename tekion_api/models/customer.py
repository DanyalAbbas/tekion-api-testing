from pydantic import BaseModel, Field, model_validator


class Vehicle(BaseModel):
    """A vehicle linked to a customer record."""
    model_config = {"extra": "ignore"}

    vehicle_id: str | None = Field(None, alias="vehicleId")
    vin: str | None = None
    year: str | None = None
    make: str | None = None
    model: str | None = None
    last8_digit_vin: str | None = Field(None, alias="last8DigitVIN")


class Customer(BaseModel):
    """A Tekion customer record.

    The Tekion API returns customer data in a nested structure:
    {
      "id": "...",
      "displayId": "...",
      "vehicles": [{ "vin": "...", "make": "...", "model": "...", ... }],
      "customerDetails": {
        "name": { "firstName": "...", "lastName": "..." },
        "phoneCommunications": [{ "phone": { "completeNumber": "+1..." } }],
        "emailCommunications": [{ "email": "..." }],
        "customerType": "INDIVIDUAL"
      },
      "status": "ACTIVE"
    }

    This model flattens that structure using a validator.
    New fields from Tekion are silently ignored.
    """
    model_config = {"extra": "ignore"}

    id: str | None = None
    display_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    customer_type: str | None = None
    status: str | None = None
    vehicles: list[Vehicle] = []

    @model_validator(mode="before")
    @classmethod
    def _extract_customer_details(cls, data: dict) -> dict:
        """Flatten the nested customerDetails into top-level fields."""
        details = data.get("customerDetails") or {}
        name = details.get("name") or {}
        phone_comms = details.get("phoneCommunications") or []
        email_comms = details.get("emailCommunications") or []

        # Extract first preferred phone number's complete number
        phone = None
        for comm in phone_comms:
            p = comm.get("phone") or {}
            phone = p.get("completeNumber") or p.get("localNumber")
            if phone:
                break

        # Extract first email
        email = None
        for comm in email_comms:
            email = comm.get("email")
            if email:
                break

        # Parse vehicles
        raw_vehicles = data.get("vehicles") or []
        vehicles = []
        for v in raw_vehicles:
            vehicles.append(Vehicle.model_validate(v))

        return {
            "id": data.get("id"),
            "display_id": data.get("displayId"),
            "first_name": name.get("firstName"),
            "last_name": name.get("lastName"),
            "phone": phone,
            "email": email,
            "customer_type": details.get("customerType"),
            "status": data.get("status"),
            "vehicles": vehicles,
        }


class CreateCustomerRequest(BaseModel):
    """Builds the minimal Tekion Create Customer payload.

    Only includes fields necessary for voice-agent intake.
    """
    first_name: str
    last_name: str
    phone: str
    country_code: int = 1

    def to_dict(self) -> dict:
        """Convert to the nested Tekion JSON structure."""
        return {
            "status": "ACTIVE",
            "customerDetails": {
                "customerType": "INDIVIDUAL",
                "phoneCommunications": [
                    {
                        "phoneType": "MOBILE",
                        "phone": {
                            "countryCode": self.country_code,
                            "localNumber": self.phone,
                        },
                        "usagePreference": {
                            "preferred": True,
                            "preferenceMapping": {
                                "MARKETING": "NO",
                                "TRANSACTION": "YES",
                            },
                        },
                    }
                ],
                "name": {
                    "firstName": self.first_name,
                    "lastName": self.last_name,
                },
            },
        }


class UpdateCustomerRequest(CreateCustomerRequest):
    """Same payload structure as Create, but the caller supplies the ID to the service method."""
    pass
