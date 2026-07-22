import logging

from tekion_api.client import ApiClient
from tekion_api.services.base import ServiceBase

logger = logging.getLogger(__name__)

RO_PATH = "/v4.0.0/repair-orders"


class RepairOrderService(ServiceBase):
    def __init__(self, client: ApiClient):
        super().__init__(client)

    def search(self, *, filters: list[dict] | None = None,
               pagination_token: str | None = None,
               page_size: int = 20, **extra) -> dict:
        body: dict[str, object] = {"pageSize": page_size}
        if pagination_token:
            body["paginationToken"] = pagination_token
        if filters:
            body["filters"] = filters
        if extra:
            body.update(extra)
        return self._client.post(f"{RO_PATH}:search", json=body)

    def get(self, ro_id: str) -> dict:
        return self._client.get(f"{RO_PATH}/{ro_id}")

    def get_customer(self, ro_id: str, ro_customer_id: str) -> dict:
        return self._client.get(f"{RO_PATH}/{ro_id}/ro-customers/{ro_customer_id}")

    def get_vehicle(self, ro_id: str) -> dict:
        return self._client.get(f"{RO_PATH}/{ro_id}/ro-vehicle")

    def get_jobs(self, ro_id: str) -> dict:
        return self._client.get(f"{RO_PATH}/{ro_id}/jobs")

    def create(self, *, billing_customer_id: str, primary_customer_id: str,
               vin: str, mileage_in: int = 0, license_plate: str | None = None,
               tag_number: str | None = None, transportation_id: str | None = None,
               service_advisor_id: str | None = None,
               drop_off_customer_id: str | None = None,
               **extra) -> dict:
        body = {
            "billingCustomerId": billing_customer_id,
            "primaryCustomerId": primary_customer_id,
            "vehicle": {"vin": vin, "mileageIn": mileage_in},
        }
        if license_plate:
            body["vehicle"]["licensePlate"] = license_plate
        if tag_number:
            body["tagNumber"] = tag_number
        if transportation_id:
            body["transportationId"] = transportation_id
        if service_advisor_id:
            body["serviceAdvisorId"] = service_advisor_id
        if drop_off_customer_id:
            body["dropOffCustomerId"] = drop_off_customer_id
        body.update(extra)
        return self._client.post(RO_PATH, json=body)

    def create_from_appointment(self, appointment_id: str, tag_number: str | None = None,
                                **extra) -> dict:
        body = {"appointmentId": appointment_id}
        if tag_number:
            body["tagNumber"] = tag_number
        body.update(extra)
        return self._client.post(f"{RO_PATH}:appointment-to-ro", json=body)

    def create_job(self, ro_id: str, *, pay_type: str = "CUSTOMER_PAY",
                   job_type: str = "UVI", concern_text: str,
                   concern_type: str = "CUSTOMER_CONCERN",
                   opcode: str, opcode_description: str | None = None,
                   labor_sale_amount: float = 0, bill_duration: int = 0,
                   labor_allowance_duration: int = 0,
                   parts: list[dict] | None = None,
                   **extra) -> dict:
        operation = {
            "opcode": opcode,
            "labor": {
                "saleAmount": labor_sale_amount,
                "billDuration": bill_duration,
                "laborAllowanceDuration": labor_allowance_duration,
            },
        }
        if opcode_description:
            operation["opcodeDescription"] = opcode_description
        if parts:
            operation["parts"] = parts

        body = {
            "payType": pay_type,
            "type": job_type,
            "concern": {"type": concern_type, "text": concern_text},
            "operations": [operation],
        }
        body.update(extra)
        return self._client.post(f"{RO_PATH}/{ro_id}/jobs", json=body)

    def create_operation(self, ro_id: str, job_id: str, *,
                         opcode: str, opcode_description: str | None = None,
                         labor_sale_amount: float = 0, bill_duration: int = 0,
                         labor_allowance_duration: int = 0,
                         parts: list[dict] | None = None,
                         **extra) -> dict:
        operation = {
            "opcode": opcode,
            "labor": {
                "saleAmount": labor_sale_amount,
                "billDuration": bill_duration,
                "laborAllowanceDuration": labor_allowance_duration,
            },
        }
        if opcode_description:
            operation["opcodeDescription"] = opcode_description
        if parts:
            operation["parts"] = parts

        body = {"operations": [operation]}
        body.update(extra)
        return self._client.post(f"{RO_PATH}/{ro_id}/jobs/{job_id}/operations", json=body)

    def create_operation_parts(self, ro_id: str, job_id: str, operation_id: str,
                               parts: list[dict], **extra) -> dict:
        body: dict[str, object] = {"parts": parts}
        body.update(extra)
        return self._client.post(
            f"{RO_PATH}/{ro_id}/jobs/{job_id}/operations/{operation_id}/parts", json=body)

    def get_part(self, ro_id: str, job_id: str, operation_id: str, part_id: str) -> dict:
        return self._client.get(
            f"{RO_PATH}/{ro_id}/jobs/{job_id}/operations/{operation_id}/parts/{part_id}")

    def get_parts(self, ro_id: str, job_id: str, operation_id: str) -> dict:
        return self._client.get(
            f"{RO_PATH}/{ro_id}/jobs/{job_id}/operations/{operation_id}/parts")

    def get_operation_part_fees(self, ro_id: str, job_id: str,
                                operation_id: str, part_id: str) -> dict:
        return self._client.get(
            f"{RO_PATH}/{ro_id}/jobs/{job_id}/operations/{operation_id}/parts/{part_id}/part-fees")

    def get_invoices(self, ro_id: str) -> dict:
        return self._client.get(f"{RO_PATH}/{ro_id}/ro-invoices")

    def get_invoice(self, ro_id: str, invoice_id: str) -> dict:
        return self._client.get(f"{RO_PATH}/{ro_id}/ro-invoices/{invoice_id}")

    def update_status(self, ro_id: str, status: str, reason: str | None = None, **extra) -> dict:
        body: dict[str, object] = {"status": status}
        if reason:
            body["reason"] = reason
        body.update(extra)
        return self._client.put(f"{RO_PATH}/{ro_id}:status", json=body)
