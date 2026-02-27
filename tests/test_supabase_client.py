import pytest
from unittest.mock import patch, MagicMock
from app.core.supabase import get_supabase, reset_supabase_client


def test_get_supabase_raises_on_missing_config(monkeypatch):
    """Test that get_supabase raises ValueError when config is missing."""
    monkeypatch.setattr("app.core.supabase.SUPABASE_URL", "")
    monkeypatch.setattr("app.core.supabase.SUPABASE_KEY", "")

    # Reset client to force re-initialization
    reset_supabase_client()

    with pytest.raises(ValueError, match="Supabase URL and key must be configured"):
        get_supabase()


def test_get_supabase_creates_client(monkeypatch):
    """Test that get_supabase creates client when config is present."""
    monkeypatch.setattr("app.core.supabase.SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setattr("app.core.supabase.SUPABASE_KEY", "test-key")

    # Reset client to force re-initialization
    reset_supabase_client()

    with patch("app.core.supabase.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        client = get_supabase()

        assert client is mock_client
        mock_create.assert_called_once_with("https://test.supabase.co", "test-key")


def test_get_supabase_returns_cached_client(monkeypatch):
    """Test that get_supabase returns cached client on subsequent calls."""
    monkeypatch.setattr("app.core.supabase.SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setattr("app.core.supabase.SUPABASE_KEY", "test-key")

    # Reset client
    reset_supabase_client()

    with patch("app.core.supabase.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        # First call creates client
        client1 = get_supabase()
        # Second call returns cached
        client2 = get_supabase()

        assert client1 is client2
        mock_create.assert_called_once()  # Only called once


def test_reset_supabase_client():
    """Test that reset_supabase_client clears the cached client."""
    reset_supabase_client()

    # After reset, internal client should be None
    import app.core.supabase as supabase_module

    assert supabase_module._supabase_client is None
