"""Tests for the integrated ingestion pipeline.

The /api/v1/ingest endpoint uses an async enqueue model — it returns 202 Accepted
immediately with a job_id and status_url. The heavy PDF extraction runs in a
background worker. These tests verify the API contract, not the worker behaviour.
"""

import io
import os
from unittest.mock import patch

import pytest

from app.main import app
from tests.conftest import get_categorized_pdf_paths


# ---------------------------------------------------------------------------
# Lazy PDF discovery — uses conftest helpers, safe when directories absent.
# ---------------------------------------------------------------------------

ALL_PDF_PATHS, VECTOR_PDF_PATHS, RASTER_PDF_PATHS = get_categorized_pdf_paths()
ALL_PDF_NAMES = [os.path.basename(p) for p in ALL_PDF_PATHS]
VECTOR_PDF_NAMES = [os.path.basename(p) for p in VECTOR_PDF_PATHS]
RASTER_PDF_NAMES = [os.path.basename(p) for p in RASTER_PDF_PATHS]


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# Basic smoke / validation tests (no PDF required)
# ---------------------------------------------------------------------------


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "version" in data


def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert "message" in data
    assert "ArchAI BOM" in data["message"]


def test_api_ingest_endpoint_no_file(client):
    """Endpoint returns 400 when no file is provided."""
    response = client.post("/api/v1/ingest")
    assert response.status_code == 400
    assert "No file provided" in response.get_json()["error"]


def test_api_ingest_endpoint_invalid_file(client):
    """Endpoint returns 400 for non-PDF uploads."""
    data = {"file": (io.BytesIO(b"dummy content"), "test_floorplan.txt")}
    response = client.post(
        "/api/v1/ingest",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "must be a PDF" in response.get_json()["error"]


@patch("app.api.ingest_service.enqueue_ingest_job")
@patch("app.api.ingest_service.create_job", return_value=99)
def test_api_ingest_endpoint_returns_202(mock_create_job, mock_enqueue, client):
    """Valid PDF upload enqueues a job and returns the 202 async contract."""
    pdf_path = "sample_pdfs/vector/test_floorplan.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"{pdf_path} not found")

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/ingest",
            data={"file": (f, "test_floorplan.pdf")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 202
    data = response.get_json()
    assert data["job_id"] == 99
    assert data["status"] == "queued"
    assert data["status_url"] == "/api/v1/jobs/99"

    mock_create_job.assert_called_once()
    call_kwargs = mock_create_job.call_args.kwargs
    assert call_kwargs["job_type"] == "ingest"

    mock_enqueue.assert_called_once_with(99)


# =============================================================================
# VECTOR PDF INGESTION TESTS
# =============================================================================


@pytest.mark.skipif(not VECTOR_PDF_PATHS, reason="No vector PDFs found")
class TestVectorPDFIngestion:
    """Ingestion API contract tests using vector-based PDFs.

    The endpoint does not process the PDF inline — it enqueues a background job
    and returns 202 immediately.  All tests mock create_job / enqueue_ingest_job
    and verify the async response shape only.
    """

    @patch("app.api.ingest_service.enqueue_ingest_job")
    @patch("app.api.ingest_service.create_job")
    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_ingest_vector_floorplan_returns_202(
        self, mock_create_job, mock_enqueue, client, pdf_path
    ):
        """Each vector PDF upload receives a 202 with a job_id."""
        mock_create_job.return_value = 1
        pdf_name = os.path.basename(pdf_path)

        with open(pdf_path, "rb") as f:
            response = client.post(
                "/api/v1/ingest",
                data={"file": (f, pdf_name)},
                content_type="multipart/form-data",
            )

        assert response.status_code == 202, (
            f"Expected 202 for {pdf_name}, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert "status_url" in data
        assert data["status_url"] == f"/api/v1/jobs/{data['job_id']}"

    @patch("app.api.ingest_service.enqueue_ingest_job")
    @patch("app.api.ingest_service.create_job")
    def test_all_vector_floorplans_enqueue_successfully(
        self, mock_create_job, mock_enqueue, client
    ):
        """All vector PDFs trigger a job enqueue without errors."""
        mock_create_job.return_value = 1
        failed_pdfs = []

        for pdf_path in VECTOR_PDF_PATHS:
            pdf_name = os.path.basename(pdf_path)
            try:
                with open(pdf_path, "rb") as f:
                    response = client.post(
                        "/api/v1/ingest",
                        data={"file": (f, pdf_name)},
                        content_type="multipart/form-data",
                    )
                if response.status_code != 202:
                    failed_pdfs.append(
                        (pdf_name, response.status_code, response.get_json())
                    )
            except Exception as exc:
                failed_pdfs.append((pdf_name, "exception", str(exc)))

        assert not failed_pdfs, (
            f"{len(failed_pdfs)} vector PDF(s) failed to enqueue:\n"
            + "\n".join(f"  {n}: {c} — {m}" for n, c, m in failed_pdfs)
        )

    @patch("app.api.ingest_service.enqueue_ingest_job")
    @patch("app.api.ingest_service.create_job")
    def test_vector_ingest_enqueue_called_per_pdf(
        self, mock_create_job, mock_enqueue, client
    ):
        """enqueue_ingest_job is called exactly once per successful upload."""
        mock_create_job.return_value = 1

        for pdf_path in VECTOR_PDF_PATHS:
            mock_enqueue.reset_mock()
            pdf_name = os.path.basename(pdf_path)
            with open(pdf_path, "rb") as f:
                client.post(
                    "/api/v1/ingest",
                    data={"file": (f, pdf_name)},
                    content_type="multipart/form-data",
                )
            mock_enqueue.assert_called_once_with(1)


# =============================================================================
# RASTER PDF INGESTION TESTS
# =============================================================================


@pytest.mark.skipif(not RASTER_PDF_PATHS, reason="No raster PDFs found")
class TestRasterPDFIngestion:
    """Ingestion API contract tests using raster-based PDFs.

    Like vector tests, these verify the async 202 contract only.
    The Gemini vision fallback runs inside the worker, not the endpoint.
    """

    @patch("app.api.ingest_service.enqueue_ingest_job")
    @patch("app.api.ingest_service.create_job")
    @pytest.mark.parametrize("pdf_path", RASTER_PDF_PATHS, ids=RASTER_PDF_NAMES)
    def test_ingest_raster_floorplan_returns_202(
        self, mock_create_job, mock_enqueue, client, pdf_path
    ):
        """Each raster PDF upload receives a 202 with a job_id."""
        mock_create_job.return_value = 5
        pdf_name = os.path.basename(pdf_path)

        with open(pdf_path, "rb") as f:
            response = client.post(
                "/api/v1/ingest",
                data={"file": (f, pdf_name)},
                content_type="multipart/form-data",
            )

        assert response.status_code == 202, (
            f"Expected 202 for {pdf_name}, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert "status_url" in data

    @patch("app.api.ingest_service.enqueue_ingest_job")
    @patch("app.api.ingest_service.create_job")
    def test_all_raster_pdfs_enqueue_successfully(
        self, mock_create_job, mock_enqueue, client
    ):
        """All raster PDFs trigger a job enqueue without errors."""
        mock_create_job.return_value = 5
        failed = []

        for pdf_path in RASTER_PDF_PATHS:
            pdf_name = os.path.basename(pdf_path)
            with open(pdf_path, "rb") as f:
                response = client.post(
                    "/api/v1/ingest",
                    data={"file": (f, pdf_name)},
                    content_type="multipart/form-data",
                )
            if response.status_code != 202:
                failed.append((pdf_name, response.status_code, response.get_json()))

        assert not failed, f"Raster PDF(s) that failed to enqueue: {failed}"


# =============================================================================
# MIXED PDF BATCH TESTS
# =============================================================================


class TestMixedPDFBatch:
    """Tests covering PDF discovery / categorisation (no API calls)."""

    def test_pdf_categorization_complete(self):
        """Verify all discovered PDFs are categorized as vector or raster."""
        total = len(VECTOR_PDF_PATHS) + len(RASTER_PDF_PATHS)
        assert total == len(ALL_PDF_PATHS), (
            f"PDF categorization incomplete: {total} categorized vs {len(ALL_PDF_PATHS)} total"
        )

    def test_at_least_one_vector_pdf(self):
        """Ensure we have at least one vector PDF for testing."""
        assert len(VECTOR_PDF_PATHS) >= 1, "Need at least one vector PDF"

    def test_at_least_one_raster_pdf(self):
        """Ensure we have at least one raster PDF for testing."""
        assert len(RASTER_PDF_PATHS) >= 1, "Need at least one raster PDF"
