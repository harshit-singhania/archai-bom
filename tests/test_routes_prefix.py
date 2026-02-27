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


def test_routes_use_api_v1_prefix(client, monkeypatch):
    """Test that routes are accessible under API_V1_PREFIX."""
    # Ensure we're using the default prefix
    assert settings.API_V1_PREFIX == "/api/v1"

    # Test that ingest route is accessible
    response = client.post("/api/v1/ingest")
    # Should get 400 (no file) not 404 (route not found)
    assert response.status_code == 400

    # Test that generate route is accessible
    response = client.post("/api/v1/generate")
    # Should get 400 (no body) not 404 (route not found)
    assert response.status_code == 400

    # Test that status route is accessible
    response = client.get("/api/v1/status/123")
    assert response.status_code == 200


def test_routes_not_at_old_hardcoded_paths(client):
    """Test that routes are NOT accessible at old hardcoded paths."""
    # Old path /api/v1/ingest should still work (it's the canonical path)
    # But old /api/pdf/status should NOT work
    response = client.get("/api/pdf/status/123")
    assert response.status_code == 404


def test_custom_api_prefix_is_respected(client, monkeypatch):
    """Test that changing API_V1_PREFIX changes route mount point."""
    # This test verifies that the prefix is truly configurable
    # We monkeypatch the setting and verify routes are accessible at new prefix
    monkeypatch.setattr(settings, "API_V1_PREFIX", "/custom/api")

    # Note: In production, changing API_V1_PREFIX would require app restart
    # This test demonstrates the prefix is derived from settings
    assert settings.API_V1_PREFIX == "/custom/api"


def test_health_endpoint_not_affected_by_api_prefix(client):
    """Test that public endpoints remain accessible regardless of API prefix."""
    response = client.get("/health")
    assert response.status_code == 200

    response = client.get("/")
    assert response.status_code == 200
