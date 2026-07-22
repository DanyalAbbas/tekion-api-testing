import logging

from tekion_api.client import ApiClient
from tekion_api.services.base import ServiceBase

logger = logging.getLogger(__name__)

APPT_PATH = "/v4.0.0/service-appointments"


class AppointmentService(ServiceBase):
    def __init__(self, client: ApiClient):
        super().__init__(client)

    def search(self, *, filters: list[dict] | None = None,
               pagination_token: str | None = None,
               page_size: int = 25, sort: list[dict] | None = None,
               text_search: str | None = None, **extra) -> dict:
        body: dict[str, object] = {"pageSize": page_size}
        if pagination_token:
            body["paginationToken"] = pagination_token
        if filters:
            body["filters"] = filters
        if sort:
            body["sort"] = sort
        if text_search:
            body["textSearch"] = {"text": text_search}
        if extra:
            body.update(extra)
        return self._client.post(f"{APPT_PATH}:search", json=body)

    def get(self, appointment_id: str) -> dict:
        return self._client.get(f"{APPT_PATH}/{appointment_id}")
