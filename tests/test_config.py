import pytest
from tekion_api.config import TekionConfig, load_config
from tekion_api.exceptions import TekionError


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("TEKION_APP_ID", "test-app")
    monkeypatch.setenv("TEKION_SECRET_KEY", "test-secret")
    monkeypatch.setenv("TEKION_DEALER_ID", "test-dealer")
    monkeypatch.setenv("TEKION_BASE_URL", "https://api-sandbox.tekioncloud.com/openapi")

    config = load_config()
    assert config.app_id == "test-app"
    assert config.secret_key == "test-secret"
    assert config.default_dealer_id == "test-dealer"
    assert config.base_url == "https://api-sandbox.tekioncloud.com/openapi"


def test_load_config_default_base_url(monkeypatch):
    """Defaults to sandbox when TEKION_BASE_URL not set."""
    monkeypatch.setenv("TEKION_APP_ID", "test-app")
    monkeypatch.setenv("TEKION_SECRET_KEY", "test-secret")
    monkeypatch.setenv("TEKION_DEALER_ID", "test-dealer")

    config = load_config()
    assert config.base_url == "https://api-sandbox.tekioncloud.com/openapi"


def test_load_config_missing_required(monkeypatch):
    """Raises TekionError when required env vars are missing."""
    monkeypatch.delenv("TEKION_APP_ID", raising=False)
    monkeypatch.delenv("TEKION_SECRET_KEY", raising=False)
    monkeypatch.delenv("TEKION_DEALER_ID", raising=False)

    with pytest.raises(TekionError, match="TEKION_APP_ID"):
        load_config()


def test_load_config_partial_missing(monkeypatch):
    """Raises TekionError listing all missing vars."""
    monkeypatch.setenv("TEKION_APP_ID", "test-app")
    monkeypatch.delenv("TEKION_SECRET_KEY", raising=False)
    monkeypatch.delenv("TEKION_DEALER_ID", raising=False)

    with pytest.raises(TekionError, match="TEKION_SECRET_KEY"):
        load_config()
