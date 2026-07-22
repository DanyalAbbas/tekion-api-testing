from tekion_api.client import ApiClient


class ServiceBase:
    """Base class for all domain services.

    Provides shared infrastructure:
    - Client reference for API calls
    - API tier tagging for observability
    - Consistent error propagation
    """

    def __init__(self, client: ApiClient):
        self._client = client

    def _log_tier(self, tier: str, method: str, path: str) -> None:
        """Log the API call with its tier for observability."""
        pass
