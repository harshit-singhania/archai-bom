"""Async job lifecycle, worker execution, and API enqueue tests.

Covers:
  - test_job_repository_lifecycle: Task 1 verification
  - test_worker_executes_and_persists_results: Task 2 verification
  - Additional route-level and integration assertions: Task 3 verification
"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import create_engine, SQLModel

from app.core import database as db_module
from app.main import app
from app.services.job_repository import (
    create_job,
    get_job_by_id,
    list_jobs_by_floorplan,
    mark_job_running,
    mark_job_succeeded,
    mark_job_failed,
    VALID_JOB_TYPES,
    VALID_STATUSES,
)


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
# Task 1: Job repository lifecycle
# ---------------------------------------------------------------------------


class TestJobRepositoryLifecycle:
    """Verify that jobs can be created, updated, and queried durably."""

    def test_create_job_returns_integer_id(self, test_db):
        """create_job returns a positive integer primary key."""
        job_id = create_job(job_type="ingest", payload='{"pdf_path": "/tmp/x.pdf"}')
        assert isinstance(job_id, int)
        assert job_id > 0

    def test_create_job_initial_status_is_queued(self, test_db):
        """Newly created job starts in queued state."""
        job_id = create_job(job_type="ingest")
        job = get_job_by_id(job_id)
        assert job is not None
        assert job["status"] == "queued"

    def test_create_job_with_payload_and_floorplan(self, test_db):
        """Payload and floorplan_id are stored and retrievable."""
        from app.services.floorplan_repository import create_floorplan
        floorplan_id = create_floorplan(pdf_storage_url="sample.pdf", status="uploaded")

        payload = json.dumps({"pdf_path": "/tmp/sample.pdf"})
        job_id = create_job(job_type="ingest", payload=payload, floorplan_id=floorplan_id)

        job = get_job_by_id(job_id)
        assert job["job_type"] == "ingest"
        assert job["payload"] == payload
        assert job["floorplan_id"] == floorplan_id

    def test_create_generate_job(self, test_db):
        """generate job_type is accepted."""
        job_id = create_job(job_type="generate", payload='{"prompt": "Open plan"}')
        job = get_job_by_id(job_id)
        assert job["job_type"] == "generate"

    def test_create_job_rejects_unknown_type(self, test_db):
        """Unknown job_type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown job_type"):
            create_job(job_type="unknown_type")

    def test_get_job_by_id_returns_none_for_missing(self, test_db):
        """get_job_by_id returns None for non-existent ID."""
        result = get_job_by_id(999999)
        assert result is None

    def test_mark_job_running_transitions_status(self, test_db):
        """mark_job_running sets status=running and populates started_at."""
        job_id = create_job(job_type="ingest")
        result = mark_job_running(job_id)
        assert result is True

        job = get_job_by_id(job_id)
        assert job["status"] == "running"
        assert job["started_at"] is not None

    def test_mark_job_running_returns_false_for_missing(self, test_db):
        """mark_job_running returns False for non-existent job."""
        result = mark_job_running(999999)
        assert result is False

    def test_mark_job_succeeded_with_result_ref(self, test_db):
        """mark_job_succeeded records status=succeeded and result_ref."""
        job_id = create_job(job_type="ingest")
        mark_job_running(job_id)
        result_ref = {"result_type": "floorplan", "result_id": 42}
        result = mark_job_succeeded(job_id, result_ref=result_ref)
        assert result is True

        job = get_job_by_id(job_id)
        assert job["status"] == "succeeded"
        assert job["result_ref"]["result_type"] == "floorplan"
        assert job["result_ref"]["result_id"] == 42
        assert job["finished_at"] is not None

    def test_mark_job_succeeded_returns_false_for_missing(self, test_db):
        """mark_job_succeeded returns False for non-existent job."""
        result = mark_job_succeeded(999999)
        assert result is False

    def test_mark_job_failed_records_error(self, test_db):
        """mark_job_failed sets status=failed and stores error_message."""
        job_id = create_job(job_type="generate")
        mark_job_running(job_id)
        result = mark_job_failed(job_id, error_message="Gemini quota exceeded")
        assert result is True

        job = get_job_by_id(job_id)
        assert job["status"] == "failed"
        assert job["error_message"] == "Gemini quota exceeded"
        assert job["finished_at"] is not None

    def test_mark_job_failed_returns_false_for_missing(self, test_db):
        """mark_job_failed returns False for non-existent job."""
        result = mark_job_failed(999999, error_message="nope")
        assert result is False

    def test_list_jobs_by_floorplan(self, test_db):
        """list_jobs_by_floorplan returns all jobs for a floorplan."""
        from app.services.floorplan_repository import create_floorplan
        fp_id = create_floorplan(pdf_storage_url="multi.pdf", status="uploaded")

        job_id_1 = create_job(job_type="ingest", floorplan_id=fp_id)
        job_id_2 = create_job(job_type="generate", floorplan_id=fp_id)

        jobs = list_jobs_by_floorplan(fp_id)
        assert len(jobs) == 2
        job_ids = {j["id"] for j in jobs}
        assert job_id_1 in job_ids
        assert job_id_2 in job_ids

    def test_list_jobs_by_floorplan_returns_empty_for_no_jobs(self, test_db):
        """list_jobs_by_floorplan returns empty list when no jobs exist."""
        jobs = list_jobs_by_floorplan(999999)
        assert jobs == []

    def test_job_has_required_serialisation_fields(self, test_db):
        """Serialised job dict includes all required lifecycle fields."""
        job_id = create_job(job_type="ingest")
        job = get_job_by_id(job_id)

        required = {
            "id", "job_type", "status", "floorplan_id", "payload",
            "error_message", "result_ref", "created_at", "updated_at",
            "started_at", "finished_at",
        }
        for field in required:
            assert field in job, f"Missing field: {field}"

    def test_full_lifecycle_queued_running_succeeded(self, test_db):
        """Full happy-path lifecycle: queued -> running -> succeeded."""
        job_id = create_job(job_type="ingest", payload='{"pdf_path": "/tmp/test.pdf"}')

        job = get_job_by_id(job_id)
        assert job["status"] == "queued"

        mark_job_running(job_id)
        job = get_job_by_id(job_id)
        assert job["status"] == "running"

        mark_job_succeeded(job_id, result_ref={"result_type": "floorplan", "result_id": 7})
        job = get_job_by_id(job_id)
        assert job["status"] == "succeeded"

    def test_full_lifecycle_queued_running_failed(self, test_db):
        """Full failure lifecycle: queued -> running -> failed."""
        job_id = create_job(job_type="generate")

        mark_job_running(job_id)
        mark_job_failed(job_id, error_message="Generation timed out")

        job = get_job_by_id(job_id)
        assert job["status"] == "failed"
        assert job["error_message"] == "Generation timed out"


# ---------------------------------------------------------------------------
# Task 2: Worker executes and persists results
# ---------------------------------------------------------------------------


class TestWorkerExecutesAndPersistsResults:
    """Verify that the job runner executes jobs and writes final states."""

    def test_worker_executes_ingest_job_and_persists_success(self, test_db):
        """run_job for an ingest job transitions to succeeded with result_ref."""
        from app.services.job_runner import run_job
        from app.services.floorplan_repository import create_floorplan

        # Create a realistic temp PDF substitute (empty file for mock path)
        floorplan_id = create_floorplan(pdf_storage_url="runner_test.pdf", status="uploaded")
        payload = json.dumps({"pdf_path": "/tmp/fake.pdf", "floorplan_id": floorplan_id})
        job_id = create_job(job_type="ingest", payload=payload, floorplan_id=floorplan_id)

        # Mock the ingestion pipeline so we don't need a real PDF
        mock_result = MagicMock()
        mock_result.total_wall_count = 5
        mock_result.total_linear_pts = 100.0
        mock_result.source = "vector"
        mock_result.wall_segments = []

        with patch("app.services.job_runner.ingest_pdf", return_value=mock_result):
            with patch("app.services.job_runner.update_floorplan_vector_data"):
                with patch("app.services.job_runner.update_floorplan_status"):
                    run_job(job_id)

        job = get_job_by_id(job_id)
        assert job["status"] == "succeeded"
        assert job["result_ref"] is not None
        assert job["result_ref"]["result_type"] == "floorplan"
        assert job["finished_at"] is not None

    def test_worker_executes_ingest_job_and_persists_failure(self, test_db):
        """run_job for a failed ingest transitions to failed with error_message."""
        from app.services.job_runner import run_job
        from app.services.floorplan_repository import create_floorplan

        floorplan_id = create_floorplan(pdf_storage_url="fail_test.pdf", status="uploaded")
        payload = json.dumps({"pdf_path": "/tmp/bad.pdf", "floorplan_id": floorplan_id})
        job_id = create_job(job_type="ingest", payload=payload, floorplan_id=floorplan_id)

        with patch("app.services.job_runner.ingest_pdf", side_effect=RuntimeError("No API key")):
            with patch("app.services.job_runner.update_floorplan_error"):
                run_job(job_id)

        job = get_job_by_id(job_id)
        assert job["status"] == "failed"
        assert job["error_message"] is not None

    def test_worker_marks_running_before_executing(self, test_db):
        """run_job sets status=running before executing the pipeline."""
        from app.services.job_runner import run_job
        from app.services.floorplan_repository import create_floorplan

        floorplan_id = create_floorplan(pdf_storage_url="running_test.pdf", status="uploaded")
        payload = json.dumps({"pdf_path": "/tmp/x.pdf", "floorplan_id": floorplan_id})
        job_id = create_job(job_type="ingest", payload=payload, floorplan_id=floorplan_id)

        seen_statuses = []

        original_mark_running = None

        def capturing_ingest(pdf_path):
            # At the point the pipeline runs, job should already be running
            job = get_job_by_id(job_id)
            seen_statuses.append(job["status"])
            raise RuntimeError("Abort early")

        with patch("app.services.job_runner.ingest_pdf", side_effect=capturing_ingest):
            with patch("app.services.job_runner.update_floorplan_error"):
                run_job(job_id)

        assert "running" in seen_statuses

    def test_worker_handles_unknown_job_type_gracefully(self, test_db):
        """run_job with an unrecognised job_type marks the job as failed."""
        from app.services.job_runner import run_job
        from app.models.database import AsyncJob
        from app.core.database import get_session

        # Bypass create_job validation to insert a rogue job_type
        with get_session() as session:
            job = AsyncJob(job_type="mystery", status="queued")
            session.add(job)
            session.commit()
            session.refresh(job)
            job_id = job.id

        run_job(job_id)

        job = get_job_by_id(job_id)
        assert job["status"] == "failed"


# ---------------------------------------------------------------------------
# Task 3: API enqueue and poll tests
# ---------------------------------------------------------------------------


class TestAPIEnqueueAndPoll:
    """Verify that API routes enqueue jobs and status endpoint reflects state."""

    def test_ingest_returns_202_with_job_id_and_status_url(self, client, test_db):
        """POST /api/v1/ingest returns 202 with job_id and status_url."""
        # Minimal valid PDF bytes (PDF header is enough for form upload)
        pdf_bytes = b"%PDF-1.4\n"
        data = {"file": (tempfile.SpooledTemporaryFile(), "test.pdf")}

        # Build a proper multipart form upload
        import io
        pdf_io = io.BytesIO(b"%PDF-1.4\n1 0 obj\n<</Type /Catalog>>\nendobj\n%%EOF")
        pdf_io.name = "test.pdf"

        mock_result = MagicMock()
        mock_result.total_wall_count = 3
        mock_result.total_linear_pts = 60.0
        mock_result.source = "vector"
        mock_result.wall_segments = []
        mock_result.model_dump.return_value = {
            "total_wall_count": 3,
            "total_linear_pts": 60.0,
            "source": "vector",
            "wall_segments": [],
        }

        # Patch enqueue_ingest_job to return a fake job_id without real Redis
        with patch("app.api.routes.enqueue_ingest_job", return_value=1) as mock_enqueue:
            response = client.post(
                "/api/v1/ingest",
                data={"file": (pdf_io, "test.pdf")},
                content_type="multipart/form-data",
            )

        assert response.status_code == 202
        data = response.get_json()
        assert "job_id" in data
        assert "status_url" in data
        assert data["status"] == "queued"

    def test_ingest_400_when_no_file(self, client, test_db):
        """POST /api/v1/ingest returns 400 when no file is provided."""
        response = client.post("/api/v1/ingest", data={}, content_type="multipart/form-data")
        assert response.status_code == 400

    def test_ingest_400_when_not_pdf(self, client, test_db):
        """POST /api/v1/ingest returns 400 for non-PDF file."""
        import io
        txt_io = io.BytesIO(b"not a pdf")
        response = client.post(
            "/api/v1/ingest",
            data={"file": (txt_io, "data.txt")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_status_endpoint_reflects_queued_job(self, client, test_db):
        """GET /api/v1/status/<pdf_id> returns job status when job exists."""
        from app.services.floorplan_repository import create_floorplan
        floorplan_id = create_floorplan(pdf_storage_url="status_test.pdf", status="uploaded")
        job_id = create_job(job_type="ingest", floorplan_id=floorplan_id)

        response = client.get(f"/api/v1/status/{floorplan_id}")
        assert response.status_code == 200
        data = response.get_json()
        # Status endpoint should still show floorplan status
        assert "status" in data
        assert data["pdf_id"] == floorplan_id

    def test_generate_returns_202_with_job_id(self, client, test_db):
        """POST /api/v1/generate returns 202 with job_id when enqueued."""
        # Build a minimal valid spatial_graph payload
        spatial_graph = {
            "rooms": [],
            "walls": [
                {
                    "start": {"x": 0, "y": 0},
                    "end": {"x": 100, "y": 0},
                    "thickness": 10.0,
                }
            ],
            "fixtures": [],
            "scale_factor": 1.0,
        }
        payload = {
            "spatial_graph": spatial_graph,
            "prompt": "Open plan living room",
        }

        with patch("app.api.routes.enqueue_generate_job", return_value=42) as mock_gen:
            response = client.post("/api/v1/generate", json=payload)

        assert response.status_code == 202
        data = response.get_json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert "status_url" in data

    def test_generate_400_missing_spatial_graph(self, client, test_db):
        """POST /api/v1/generate returns 400 when spatial_graph is absent."""
        response = client.post("/api/v1/generate", json={"prompt": "test"})
        assert response.status_code == 400

    def test_generate_400_missing_prompt(self, client, test_db):
        """POST /api/v1/generate returns 400 when prompt is absent."""
        response = client.post(
            "/api/v1/generate",
            json={"spatial_graph": {"walls": [{"start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 0}, "thickness": 5}], "rooms": [], "fixtures": [], "scale_factor": 1.0}},
        )
        assert response.status_code == 400
