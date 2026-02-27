"""Contract tests for GET /api/v1/status/<pdf_id> endpoint."""

import pytest
from sqlmodel import create_engine, SQLModel
from unittest.mock import patch

from app.core import database as db_module
from app.main import app
from app.services.floorplan_repository import create_floorplan, update_floorplan_status, update_floorplan_error
from app.services.bom_repository import create_bom


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_db():
    """In-memory SQLite database isolated per test."""
    original_engine = db_module._engine
    original_session_maker = db_module._session_maker

    test_engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(test_engine)

    db_module._engine = test_engine
    db_module._session_maker = None

    yield test_engine

    db_module._engine = original_engine
    db_module._session_maker = original_session_maker


@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Status endpoint — 404 contract
# ---------------------------------------------------------------------------


def test_status_returns_404_for_unknown_id(client, test_db):
    """Unknown pdf_id returns 404 with stable error JSON."""
    response = client.get("/api/v1/status/99999")

    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert "99999" in data["error"]


# ---------------------------------------------------------------------------
# Status endpoint — uploaded state
# ---------------------------------------------------------------------------


def test_status_returns_uploaded_state(client, test_db):
    """Freshly created floorplan returns status=uploaded."""
    floorplan_id = create_floorplan(
        pdf_storage_url="test.pdf",
        status="uploaded",
    )

    response = client.get(f"/api/v1/status/{floorplan_id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["pdf_id"] == floorplan_id
    assert data["status"] == "uploaded"
    assert "created_at" in data
    assert "updated_at" in data
    assert data["error_message"] is None
    assert data["generation_summary"] is None


# ---------------------------------------------------------------------------
# Status endpoint — processing state
# ---------------------------------------------------------------------------


def test_status_returns_processing_state(client, test_db):
    """Floorplan updated to processing returns correct status."""
    floorplan_id = create_floorplan(pdf_storage_url="test.pdf", status="uploaded")
    update_floorplan_status(floorplan_id, "processing")

    response = client.get(f"/api/v1/status/{floorplan_id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["pdf_id"] == floorplan_id
    assert data["status"] == "processing"


# ---------------------------------------------------------------------------
# Status endpoint — processed state
# ---------------------------------------------------------------------------


def test_status_returns_processed_state(client, test_db):
    """Floorplan updated to processed returns correct status."""
    floorplan_id = create_floorplan(pdf_storage_url="test.pdf", status="uploaded")
    update_floorplan_status(floorplan_id, "processed")

    response = client.get(f"/api/v1/status/{floorplan_id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "processed"
    assert data["error_message"] is None


# ---------------------------------------------------------------------------
# Status endpoint — error state
# ---------------------------------------------------------------------------


def test_status_returns_error_state_with_message(client, test_db):
    """Floorplan in error state includes error_message in response."""
    floorplan_id = create_floorplan(pdf_storage_url="bad.pdf", status="uploaded")
    update_floorplan_error(floorplan_id, "No vector data found in PDF.")

    response = client.get(f"/api/v1/status/{floorplan_id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "error"
    assert data["error_message"] == "No vector data found in PDF."


# ---------------------------------------------------------------------------
# Status endpoint — generation summary
# ---------------------------------------------------------------------------


def test_status_includes_generation_summary_when_bom_exists(client, test_db):
    """Status response includes generation_summary when a BOM exists."""
    floorplan_id = create_floorplan(pdf_storage_url="test.pdf", status="processed")
    bom_id = create_bom(
        floorplan_id=floorplan_id,
        total_cost_inr=50000.0,
        bom_data={"items": [{"name": "Drywall", "cost": 50000}]},
    )

    response = client.get(f"/api/v1/status/{floorplan_id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "processed"
    assert data["generation_summary"] is not None
    assert data["generation_summary"]["bom_id"] == bom_id
    assert data["generation_summary"]["total_cost_inr"] == 50000.0
    assert "generated_at" in data["generation_summary"]


def test_status_generation_summary_is_null_when_no_bom(client, test_db):
    """Status response has generation_summary=null when no BOM exists."""
    floorplan_id = create_floorplan(pdf_storage_url="test.pdf", status="processed")

    response = client.get(f"/api/v1/status/{floorplan_id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["generation_summary"] is None


# ---------------------------------------------------------------------------
# Status endpoint — response schema stability
# ---------------------------------------------------------------------------


def test_status_response_has_required_fields(client, test_db):
    """Status response always includes required schema fields."""
    floorplan_id = create_floorplan(pdf_storage_url="test.pdf", status="processing")

    response = client.get(f"/api/v1/status/{floorplan_id}")

    assert response.status_code == 200
    data = response.get_json()

    required_fields = {"pdf_id", "status", "created_at", "updated_at", "error_message", "generation_summary"}
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_status_valid_status_values(client, test_db):
    """Status values are constrained to the known lifecycle states."""
    valid_statuses = ["uploaded", "processing", "processed", "error"]

    for status_value in valid_statuses:
        floorplan_id = create_floorplan(pdf_storage_url=f"test_{status_value}.pdf", status=status_value)
        response = client.get(f"/api/v1/status/{floorplan_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] in valid_statuses
