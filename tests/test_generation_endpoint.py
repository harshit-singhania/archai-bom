"""Contract tests for POST /api/v1/generate async enqueue endpoint."""

import json
from unittest.mock import patch

import pytest

from app.main import app


@pytest.fixture
def client():
    """Create a Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _request_payload() -> dict:
    """Build a minimal valid generation payload."""
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
                }
            ],
            "rooms": [],
            "scale_factor": None,
            "page_dimensions": [10000.0, 8000.0],
        },
        "prompt": "6 operatory dental clinic with reception",
    }


@patch("app.api.routes.enqueue_generate_job")
@patch("app.api.routes.create_job")
def test_generation_endpoint_success_returns_202(
    mock_create_job,
    mock_enqueue_generate_job,
    client,
):
    """Valid request enqueues job and returns 202 contract payload."""
    mock_create_job.return_value = 42

    response = client.post("/api/v1/generate", json=_request_payload())

    assert response.status_code == 202
    data = response.get_json()
    assert data == {
        "job_id": 42,
        "status": "queued",
        "status_url": "/api/v1/jobs/42",
    }

    mock_create_job.assert_called_once()
    kwargs = mock_create_job.call_args.kwargs
    assert kwargs["job_type"] == "generate"
    assert kwargs["floorplan_id"] is None

    serialised_payload = json.loads(kwargs["payload"])
    assert serialised_payload["prompt"] == _request_payload()["prompt"]
    assert serialised_payload["parallel_candidates"] > 0
    assert serialised_payload["max_workers"] > 0

    mock_enqueue_generate_job.assert_called_once_with(42)


@patch("app.api.routes.enqueue_generate_job")
@patch("app.api.routes.create_job")
def test_generation_endpoint_respects_overrides(
    mock_create_job,
    mock_enqueue_generate_job,
    client,
):
    """Request-level floorplan and concurrency overrides are forwarded to job payload."""
    mock_create_job.return_value = 7
    payload = _request_payload()
    payload["floorplan_id"] = 123
    payload["parallel_candidates"] = 3
    payload["max_workers"] = 6

    response = client.post("/api/v1/generate", json=payload)

    assert response.status_code == 202
    kwargs = mock_create_job.call_args.kwargs
    assert kwargs["floorplan_id"] == 123
    serialised_payload = json.loads(kwargs["payload"])
    assert serialised_payload["floorplan_id"] == 123
    assert serialised_payload["parallel_candidates"] == 3
    assert serialised_payload["max_workers"] == 6
    mock_enqueue_generate_job.assert_called_once_with(7)


def test_generation_endpoint_missing_prompt_returns_400(client):
    """Missing prompt should return bad request."""
    payload = _request_payload()
    payload.pop("prompt")

    response = client.post("/api/v1/generate", json=payload)

    assert response.status_code == 400
    assert "prompt" in response.get_json()["error"]


def test_generation_endpoint_missing_spatial_graph_returns_400(client):
    """Missing spatial_graph should return bad request."""
    response = client.post("/api/v1/generate", json={"prompt": "test"})

    assert response.status_code == 400
    assert "spatial_graph" in response.get_json()["error"]


def test_generation_endpoint_empty_spatial_graph_returns_400(client):
    """Spatial graph with no walls should return bad request."""
    payload = _request_payload()
    payload["spatial_graph"]["walls"] = []

    response = client.post("/api/v1/generate", json=payload)

    assert response.status_code == 400
    assert "at least one wall" in response.get_json()["error"]


def test_generation_endpoint_invalid_parallel_candidates_returns_400(client):
    """parallel_candidates must be a positive integer."""
    payload = _request_payload()
    payload["parallel_candidates"] = 0

    response = client.post("/api/v1/generate", json=payload)

    assert response.status_code == 400
    assert "parallel_candidates" in response.get_json()["error"]


def test_generation_endpoint_invalid_max_workers_returns_400(client):
    """max_workers must be a positive integer."""
    payload = _request_payload()
    payload["max_workers"] = -1

    response = client.post("/api/v1/generate", json=payload)

    assert response.status_code == 400
    assert "max_workers" in response.get_json()["error"]


def test_generation_endpoint_invalid_floorplan_id_type_returns_400(client):
    """floorplan_id must be integer when provided."""
    payload = _request_payload()
    payload["floorplan_id"] = "abc"

    response = client.post("/api/v1/generate", json=payload)

    assert response.status_code == 400
    assert "floorplan_id" in response.get_json()["error"]


@patch("app.api.routes.enqueue_generate_job", side_effect=RuntimeError("queue down"))
@patch("app.api.routes.create_job", return_value=3)
def test_generation_endpoint_enqueue_failure_returns_500(
    mock_create_job,
    mock_enqueue_generate_job,
    client,
):
    """Queue errors should return 500 with enqueue failure message."""
    response = client.post("/api/v1/generate", json=_request_payload())

    assert response.status_code == 500
    assert "Failed to enqueue job" in response.get_json()["error"]
    mock_create_job.assert_called_once()
    mock_enqueue_generate_job.assert_called_once_with(3)
