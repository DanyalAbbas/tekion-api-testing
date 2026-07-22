import pytest
from tekion_api.config import TekionConfig


@pytest.fixture
def sandbox_config():
    return TekionConfig(
        app_id="test-app-id",
        secret_key="test-secret-key",
        base_url="https://api-sandbox.tekioncloud.com/openapi",
        default_dealer_id="techmotors_4_0",
    )


# --- Test helpers for client tests ---

class _DummyTokenManager:
    """Returns a fixed token, never refreshes."""
    def get_token(self):
        return "test-token"


class _RefreshableTokenManager:
    """Tracks how many times get_token was called (proxy for refresh attempts)."""
    def __init__(self):
        self.refresh_count = 0

    def get_token(self):
        self.refresh_count += 1
        return "fresh-token"


@pytest.fixture
def _dummy_tm():
    return _DummyTokenManager()


@pytest.fixture
def _refreshable_tm():
    return _RefreshableTokenManager()
