import logging

from tekion_api.client import ApiClient
from tekion_api.services.base import ServiceBase

logger = logging.getLogger(__name__)

BASE = "/v3.1.0"


class AppointmentService(ServiceBase):
    def __init__(self, client: ApiClient):
        super().__init__(client)

    def get_slots(self, *, shop_id: str, start_date: str, end_date: str,
                  transportation_id: str | None = None,
                  service_advisor_id: str | None = None,
                  year: int | None = None, make: str | None = None,
                  model: str | None = None, opcodes: list[str] | None = None,
                  **extra) -> dict:
        body: dict[str, object] = {
            "shopId": shop_id,
            "startDate": start_date,
            "endDate": end_date,
        }
        if transportation_id:
            body["transportationId"] = transportation_id
        if service_advisor_id:
            body["serviceAdvisorId"] = service_advisor_id
        if any([year, make, model]):
            vehicle = {}
            if year: vehicle["year"] = year
            if make: vehicle["make"] = make
            if model: vehicle["model"] = model
            body["vehicleInfo"] = vehicle
        if opcodes:
            body["opcodes"] = opcodes
        body.update(extra)
        return self._client.post(f"{BASE}/appointment-slots", json=body)

    def search(self, *, appointment_id: str | None = None,
               vin: str | None = None, customer_id: str | None = None,
               start_time: str | None = None, end_time: str | None = None,
               appointment_start_time: str | None = None,
               appointment_end_time: str | None = None,
               created_start_time: str | None = None,
               created_end_time: str | None = None,
               next_fetch_key: str | None = None,
               **extra) -> dict:
        params: dict[str, str] = {}
        if appointment_id: params["id"] = appointment_id
        if vin: params["vin"] = vin
        if customer_id: params["customerId"] = customer_id
        if start_time: params["startTime"] = start_time
        if end_time: params["endTime"] = end_time
        if appointment_start_time: params["appointmentStartTime"] = appointment_start_time
        if appointment_end_time: params["appointmentEndTime"] = appointment_end_time
        if created_start_time: params["createdStartTime"] = created_start_time
        if created_end_time: params["createdEndTime"] = created_end_time
        if next_fetch_key: params["nextFetchKey"] = next_fetch_key
        params.update(extra)
        return self._client.get(f"{BASE}/appointments", params=params)

    def create(self, *, shop_id: str, appointment_date_time: int,
               customer: dict, vehicle: dict,
               transportation_type_id: str | None = None,
               service_advisor_id: str | None = None,
               jobs: list[dict] | None = None,
               delivery_contact: dict | None = None,
               customer_comments: str | None = None,
               notify_customer: bool = False,
               post_tax_total: dict | None = None,
               **extra) -> dict:
        body: dict[str, object] = {
            "shopId": shop_id,
            "appointmentDateTime": appointment_date_time,
            "customer": customer,
            "vehicle": vehicle,
        }
        if transportation_type_id:
            body["transportationTypeId"] = transportation_type_id
        if service_advisor_id:
            body["serviceAdvisorId"] = service_advisor_id
        if jobs:
            body["jobs"] = jobs
        if delivery_contact:
            body["deliveryContact"] = delivery_contact
            body["deliveryContactSameAsCustomer"] = False
        if customer_comments:
            body["customerComments"] = customer_comments
        body["notifyCustomer"] = notify_customer
        if post_tax_total:
            body["postTaxTotalAmount"] = post_tax_total
        body.update(extra)
        return self._client.post(f"{BASE}/appointments", json=body)

    def update(self, *, id: str, shop_id: str,
               appointment_date_time: int,
               customer: dict, vehicle: dict,
               transportation_type_id: str | None = None,
               service_advisor_id: str | None = None,
               jobs: list[dict] | None = None,
               updated_jobs: list[dict] | None = None,
               deleted_jobs: list[str] | None = None,
               delivery_contact: dict | None = None,
               customer_comments: str | None = None,
               notify_customer: bool = False,
               post_tax_total: dict | None = None,
               **extra) -> dict:
        body: dict[str, object] = {
            "id": id,
            "shopId": shop_id,
            "appointmentDateTime": appointment_date_time,
            "customer": customer,
            "vehicle": vehicle,
        }
        if transportation_type_id:
            body["transportationTypeId"] = transportation_type_id
        if service_advisor_id:
            body["serviceAdvisorId"] = service_advisor_id
        if jobs:
            body["jobs"] = jobs
        if updated_jobs:
            body["updatedJobs"] = updated_jobs
        if deleted_jobs:
            body["deletedJobs"] = deleted_jobs
        if delivery_contact:
            body["deliveryContact"] = delivery_contact
            body["deliveryContactSameAsCustomer"] = False
        if customer_comments:
            body["customerComments"] = customer_comments
        body["notifyCustomer"] = notify_customer
        if post_tax_total:
            body["postTaxTotalAmount"] = post_tax_total
        body.update(extra)
        return self._client.put(f"{BASE}/appointments", json=body)

    def cancel(self, id: str, cancel_reason: str | None = None,
               do_not_notify_customer: bool = False, **extra) -> dict:
        body: dict[str, object] = {"id": id}
        if cancel_reason:
            body["cancelReason"] = cancel_reason
        body["donotNotifyCustomer"] = do_not_notify_customer
        body.update(extra)
        return self._client.post(f"{BASE}/appointments/cancel", json=body)
