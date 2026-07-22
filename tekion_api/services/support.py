import logging

from tekion_api.client import ApiClient
from tekion_api.services.base import ServiceBase

logger = logging.getLogger(__name__)

TRANSPORT_PATH = "/v4.0.0/transportation-types"


class SupportService(ServiceBase):
    def __init__(self, client: ApiClient):
        super().__init__(client)

    def get_transportation_types(self) -> dict:
        return self._client.get(TRANSPORT_PATH)

    def get_transportation_type(self, transport_id: str) -> dict:
        return self._client.get(f"{TRANSPORT_PATH}/{transport_id}")
