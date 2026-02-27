import pytest
from unittest.mock import patch
from scripts.setup_supabase_schema import get_database_url


def test_get_database_url_success(monkeypatch):
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PROJECT_URL",
        "https://xyz123.supabase.co",
    )
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PASSWORD", "secretpass"
    )

    url = get_database_url()
    assert url == "postgresql://postgres:secretpass@db.xyz123.supabase.co:5432/postgres"


def test_get_database_url_with_trailing_slash(monkeypatch):
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PROJECT_URL",
        "https://xyz123.supabase.co/",
    )
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PASSWORD", "secretpass"
    )

    url = get_database_url()
    assert url == "postgresql://postgres:secretpass@db.xyz123.supabase.co:5432/postgres"


def test_get_database_url_missing_url(monkeypatch):
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PROJECT_URL", ""
    )
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PASSWORD", "secretpass"
    )

    with pytest.raises(ValueError, match="SUPABASE_PROJECT_URL not set"):
        get_database_url()


def test_get_database_url_missing_https(monkeypatch):
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PROJECT_URL",
        "xyz123.supabase.co",
    )
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PASSWORD", "secretpass"
    )

    with pytest.raises(ValueError, match="must start with https://"):
        get_database_url()


def test_get_database_url_invalid_domain(monkeypatch):
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PROJECT_URL",
        "https://xyz123.example.com",
    )
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PASSWORD", "secretpass"
    )

    with pytest.raises(ValueError, match="must be a supabase.co domain"):
        get_database_url()


def test_get_database_url_missing_password(monkeypatch):
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PROJECT_URL",
        "https://xyz123.supabase.co",
    )
    monkeypatch.setattr("scripts.setup_supabase_schema.settings.SUPABASE_PASSWORD", "")

    with pytest.raises(ValueError, match="SUPABASE_PASSWORD not set in .env"):
        get_database_url()


def test_get_database_url_empty_project_ref(monkeypatch):
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PROJECT_URL",
        "https://.supabase.co",
    )
    monkeypatch.setattr(
        "scripts.setup_supabase_schema.settings.SUPABASE_PASSWORD", "secretpass"
    )

    with pytest.raises(ValueError, match="Could not extract project ref"):
        get_database_url()
