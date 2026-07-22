import os
from dataclasses import dataclass

from tekion_api.exceptions import TekionError

SANDBOX_BASE_URL = "https://api-sandbox.tekioncloud.com/openapi"
PRODUCTION_BASE_URL = "https://api.tekioncloud.com/openapi"


@dataclass(frozen=True)
class TekionConfig:
    app_id: str
    secret_key: str
    base_url: str = SANDBOX_BASE_URL
    default_dealer_id: str = ""
    token_cache_ttl: int = 82800  # 23 hours in seconds (safety margin below 24h)


def load_config() -> TekionConfig:
    """Load Tekion configuration from environment variables.

    Required:
        TEKION_APP_ID
        TEKION_SECRET_KEY
        TEKION_DEALER_ID

    Optional:
        TEKION_BASE_URL (defaults to sandbox)
        TEKION_TOKEN_CACHE_TTL (defaults to 82800)
    """
    missing = []
    app_id = os.getenv("TEKION_APP_ID")
    if not app_id:
        missing.append("TEKION_APP_ID")

    secret_key = os.getenv("TEKION_SECRET_KEY")
    if not secret_key:
        missing.append("TEKION_SECRET_KEY")

    dealer_id = os.getenv("TEKION_DEALER_ID")
    if not dealer_id:
        missing.append("TEKION_DEALER_ID")

    if missing:
        raise TekionError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Set them in .env or export them."
        )

    base_url = os.getenv("TEKION_BASE_URL", SANDBOX_BASE_URL)
    ttl_str = os.getenv("TEKION_TOKEN_CACHE_TTL", "")
    ttl = int(ttl_str) if ttl_str else 82800

    return TekionConfig(
        app_id=app_id,
        secret_key=secret_key,
        base_url=base_url,
        default_dealer_id=dealer_id,
        token_cache_ttl=ttl,
    )
