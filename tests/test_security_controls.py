import pytest
from unittest.mock import patch
from app.core.config import settings
from app.main import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def client_with_auth():
    """Create a test client with API auth enabled."""
    app.config["TESTING"] = True
    # Store original values
    original_debug = settings.DEBUG
    original_auth_key = settings.API_AUTH_KEY

    # Enable auth (non-debug mode with auth key)
    settings.DEBUG = False
    settings.API_AUTH_KEY = "test-api-key"

    with app.test_client() as test_client:
        yield test_client

    # Restore original values
    settings.DEBUG = original_debug
    settings.API_AUTH_KEY = original_auth_key


def test_api_requires_auth_key(client_with_auth):
    """Test that API endpoints require valid API key in production."""
    # Request without API key should fail
    response = client_with_auth.post("/api/v1/generate")
    assert response.status_code == 401
    assert "API key required" in response.get_json()["error"]

    # Request with wrong API key should fail
    response = client_with_auth.post(
        "/api/v1/generate", headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401
    assert "Invalid API key" in response.get_json()["error"]

    # Request with correct API key should proceed (may fail for other reasons)
    response = client_with_auth.post(
        "/api/v1/generate", headers={"X-API-Key": "test-api-key"}
    )
    # Should not be 401 (might be 400 for missing body, but not auth failure)
    assert response.status_code != 401


def test_public_endpoints_no_auth_required(client_with_auth):
    """Test that public endpoints don't require API key."""
    response = client_with_auth.get("/health")
    assert response.status_code == 200

    response = client_with_auth.get("/")
    assert response.status_code == 200


def test_debug_mode_allows_unauthenticated(client, monkeypatch):
    """Test that DEBUG mode allows requests without API key."""
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "API_AUTH_KEY", "")

    # Should not require auth in debug mode
    response = client.post("/api/v1/generate")
    assert response.status_code != 401


def test_cors_origins_configurable(monkeypatch):
    """Test that CORS origins are configurable."""
    # Test with specific origins
    monkeypatch.setattr(
        settings, "ALLOWED_ORIGINS", "https://example.com,https://app.example.com"
    )
    origins = settings.ALLOWED_ORIGINS.split(",")
    assert origins == ["https://example.com", "https://app.example.com"]

    # Test with wildcard
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", "*")
    assert settings.ALLOWED_ORIGINS == "*"


def test_max_content_length_configured():
    """Test that max content length is configured."""
    assert settings.MAX_CONTENT_LENGTH == 16 * 1024 * 1024  # 16MB


def test_production_requires_secret_key(monkeypatch):
    """Test that production startup fails without explicit SECRET_KEY."""
    import importlib
    import app.main as main_module

    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "SECRET_KEY", "")

    # Re-importing should raise RuntimeError
    with pytest.raises(RuntimeError, match="SECRET_KEY must be set explicitly"):
        importlib.reload(main_module)
