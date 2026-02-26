"""Integration tests for POST /api/v1/generate endpoint."""

from unittest.mock import patch

import pytest

from app.core.config import settings
from app.main import app
from app.models.constraints import (
    ConstraintResult,
    ConstraintViolation,
    ConstraintViolationType,
)
from app.models.generation import GenerationResult
from app.models.layout import GeneratedLayout


@pytest.fixture
def client():
    """Create a Flask test client."""

    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _request_payload() -> dict:
    return {
        "spatial_graph": {
            "walls": [
                {
                    "x1": 0.0,
                    "y1": 0.0,
                    "x2": 10000.0,
                    "y2": 0.0,
                    "length_pts": 10000.0,
                    "thickness": 2.0,
                },
                {
                    "x1": 10000.0,
                    "y1": 0.0,
                    "x2": 10000.0,
                    "y2": 8000.0,
                    "length_pts": 8000.0,
                    "thickness": 2.0,
                },
            ],
            "rooms": [],
            "scale_factor": None,
            "page_dimensions": [10000.0, 8000.0],
        },
        "prompt": "6 operatory dental clinic with reception",
    }


def _layout() -> GeneratedLayout:
    return GeneratedLayout(
        rooms=[
            {
                "name": "Reception",
                "room_type": "reception",
                "boundary": [
                    (0.0, 0.0),
                    (3500.0, 0.0),
                    (3500.0, 2500.0),
                    (0.0, 2500.0),
                    (0.0, 0.0),
                ],
                "area_sqm": 8.75,
            }
        ],
        interior_walls=[],
        doors=[],
        fixtures=[],
        grid_size_mm=50,
        prompt="6 operatory dental clinic with reception",
        perimeter_walls=[],
        page_dimensions_mm=(10000.0, 8000.0),
    )


@patch("app.api.routes.generate_validated_layout")
def test_generation_endpoint_success(mock_generate_validated_layout, client):
    """Valid request returns 200 with generated layout payload."""

    result = GenerationResult(
        layout=_layout(),
        success=True,
        iterations_used=1,
        constraint_history=[
            ConstraintResult(passed=True, violations=[], summary="0 errors, 0 warnings")
        ],
        error_message=None,
    )
    mock_generate_validated_layout.return_value = result

    response = client.post("/api/v1/generate", json=_request_payload())

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["iterations_used"] == 1
    assert data["layout"] is not None
    assert data["constraint_result"]["passed"] is True
    assert data["error_message"] is None

    call_kwargs = mock_generate_validated_layout.call_args.kwargs
    assert call_kwargs["parallel_candidates"] == settings.GENERATION_PARALLEL_CANDIDATES
    assert call_kwargs["max_workers"] == settings.GENERATION_MAX_WORKERS


@patch("app.api.routes.generate_validated_layout")
def test_generation_endpoint_validation_failure_returns_422(
    mock_generate_validated_layout, client
):
    """Failed validation after retries returns 422 with last layout and error."""

    violation = ConstraintViolation(
        type=ConstraintViolationType.ROOM_OVERLAP,
        description="Room A and Room B overlap by 2.0 sqm.",
        severity="error",
        affected_elements=["Room A", "Room B"],
    )
    result = GenerationResult(
        layout=_layout(),
        success=False,
        iterations_used=3,
        constraint_history=[
            ConstraintResult(
                passed=False,
                violations=[violation],
                summary="1 errors, 0 warnings",
            )
        ],
        error_message="Layout failed validation after 3 attempts",
    )
    mock_generate_validated_layout.return_value = result

    response = client.post("/api/v1/generate", json=_request_payload())

    assert response.status_code == 422
    data = response.get_json()
    assert data["success"] is False
    assert data["layout"] is not None
    assert data["error_message"] == "Layout failed validation after 3 attempts"


def test_generation_endpoint_missing_prompt_returns_400(client):
    """Missing prompt should return bad request."""

    payload = _request_payload()
    payload.pop("prompt")

    response = client.post("/api/v1/generate", json=payload)

    assert response.status_code == 400
    assert "prompt" in response.get_json()["error"]


def test_generation_endpoint_empty_spatial_graph_returns_400(client):
    """Spatial graph with no walls should return bad request."""

    payload = _request_payload()
    payload["spatial_graph"]["walls"] = []

    response = client.post("/api/v1/generate", json=payload)

    assert response.status_code == 400
    assert "at least one wall" in response.get_json()["error"]


@patch("app.api.routes.generate_validated_layout")
def test_generation_endpoint_respects_concurrency_overrides(
    mock_generate_validated_layout, client
):
    """Request-level concurrency overrides should be passed to pipeline."""

    result = GenerationResult(
        layout=_layout(),
        success=True,
        iterations_used=1,
        constraint_history=[
            ConstraintResult(passed=True, violations=[], summary="0 errors, 0 warnings")
        ],
        error_message=None,
    )
    mock_generate_validated_layout.return_value = result

    payload = _request_payload()
    payload["parallel_candidates"] = 3
    payload["max_workers"] = 6

    response = client.post("/api/v1/generate", json=payload)

    assert response.status_code == 200
    call_kwargs = mock_generate_validated_layout.call_args.kwargs
    assert call_kwargs["parallel_candidates"] == 3
    assert call_kwargs["max_workers"] == 6


def test_generation_endpoint_invalid_parallel_candidates_returns_400(client):
    """parallel_candidates must be a positive integer."""

    payload = _request_payload()
    payload["parallel_candidates"] = 0

    response = client.post("/api/v1/generate", json=payload)

    assert response.status_code == 400
    assert "parallel_candidates" in response.get_json()["error"]
