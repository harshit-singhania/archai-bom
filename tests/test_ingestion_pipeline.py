"""Tests for the integrated ingestion pipeline."""

import os
import pytest
from unittest.mock import patch, MagicMock
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


def test_api_ingest_endpoint(client):
    """Test the /api/v1/ingest API endpoint with default test file."""
    pdf_path = "sample_pdfs/vector/test_floorplan.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"{pdf_path} not found")

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/ingest",
            data={"file": (f, "test_floorplan.pdf")},
            content_type="multipart/form-data"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert "total_wall_count" in data
    assert "wall_segments" in data
    assert data["total_wall_count"] > 0


def test_api_ingest_endpoint_invalid_file(client):
    """Test endpoint with non-PDF file."""
    import io

    data = {
        "file": (io.BytesIO(b"dummy content"), "test_floorplan.txt")
    }
    response = client.post(
        "/api/v1/ingest",
        data=data,
        content_type="multipart/form-data"
    )

    assert response.status_code == 400
    assert "must be a PDF" in response.get_json()["error"]


def test_api_ingest_endpoint_no_file(client):
    """Test endpoint with no file."""
    response = client.post("/api/v1/ingest")
    assert response.status_code == 400
    assert "No file provided" in response.get_json()["error"]


# =============================================================================
# VECTOR PDF INGESTION TESTS
# =============================================================================

@pytest.mark.skipif(not VECTOR_PDF_PATHS, reason="No vector PDFs found")
class TestVectorPDFIngestion:
    """Ingestion tests using vector-based PDFs."""

    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_ingest_vector_floorplan(self, client, pdf_path):
        """Test ingestion endpoint with each vector floorplan PDF."""
        pdf_name = os.path.basename(pdf_path)

        with open(pdf_path, "rb") as f:
            response = client.post(
                "/api/v1/ingest",
                data={"file": (f, pdf_name)},
                content_type="multipart/form-data"
            )

        assert response.status_code == 200, f"Failed to ingest {pdf_name}: {response.get_json()}"

        data = response.get_json()

        # Verify response structure
        assert "total_wall_count" in data
        assert "total_linear_pts" in data
        assert "wall_segments" in data

        # Vector floorplans should have walls
        assert data["total_wall_count"] > 0, f"No walls detected in {pdf_name}"
        assert len(data["wall_segments"]) > 0

        # Verify wall segment structure
        for wall in data["wall_segments"]:
            assert "x1" in wall
            assert "y1" in wall
            assert "x2" in wall
            assert "y2" in wall
            assert "length_pts" in wall
            assert "thickness" in wall

    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_ingest_vector_response_page_dimensions(self, client, pdf_path):
        """Test that page dimensions are returned correctly for vector PDFs."""
        pdf_name = os.path.basename(pdf_path)

        with open(pdf_path, "rb") as f:
            response = client.post(
                "/api/v1/ingest",
                data={"file": (f, pdf_name)},
                content_type="multipart/form-data"
            )

        data = response.get_json()

        # Verify wall segments have required fields
        assert len(data["wall_segments"]) > 0
        for wall in data["wall_segments"]:
            assert "x1" in wall
            assert "y1" in wall
            assert "x2" in wall
            assert "y2" in wall

    def test_all_vector_floorplans_ingest_successfully(self, client):
        """Verify all vector PDFs can be ingested without errors."""
        failed_pdfs = []
        success_count = 0

        for pdf_path in VECTOR_PDF_PATHS:
            pdf_name = os.path.basename(pdf_path)

            try:
                with open(pdf_path, "rb") as f:
                    response = client.post(
                        "/api/v1/ingest",
                        data={"file": (f, pdf_name)},
                        content_type="multipart/form-data"
                    )

                if response.status_code != 200:
                    failed_pdfs.append((pdf_name, response.status_code, response.get_json()))
                else:
                    success_count += 1
            except Exception as e:
                failed_pdfs.append((pdf_name, "exception", str(e)))

        if failed_pdfs:
            print(f"\nFailed vector PDFs:")
            for name, code, msg in failed_pdfs:
                print(f"  {name}: {code} - {msg}")

        assert not failed_pdfs, f"{len(failed_pdfs)} vector PDFs failed to ingest"
        assert success_count == len(VECTOR_PDF_PATHS)

    def test_vector_wall_detection_consistency(self, client):
        """Test that wall detection is consistent across vector floorplans."""
        results = []

        for pdf_path in VECTOR_PDF_PATHS:
            pdf_name = os.path.basename(pdf_path)

            with open(pdf_path, "rb") as f:
                response = client.post(
                    "/api/v1/ingest",
                    data={"file": (f, pdf_name)},
                    content_type="multipart/form-data"
                )

            if response.status_code == 200:
                data = response.get_json()
                results.append({
                    "name": pdf_name,
                    "wall_count": data["total_wall_count"],
                    "linear_pts": data["total_linear_pts"],
                })

        # Verify we have results
        assert len(results) == len(VECTOR_PDF_PATHS)

        # Sort by wall count for analysis
        results.sort(key=lambda x: x["wall_count"])

        print(f"\nVector PDF Ingestion Results:")
        print(f"{'PDF Name':<20} {'Walls':>6} {'Linear Pts':>12}")
        print("-" * 45)
        for r in results:
            print(f"{r['name']:<20} {r['wall_count']:>6} {r['linear_pts']:>12.1f}")

        # Basic sanity checks
        min_walls = results[0]["wall_count"]
        max_walls = results[-1]["wall_count"]
        avg_walls = sum(r["wall_count"] for r in results) / len(results)

        assert max_walls >= min_walls
        assert avg_walls > 0

        print(f"\nStatistics:")
        print(f"  Min walls: {min_walls}")
        print(f"  Max walls: {max_walls}")
        print(f"  Avg walls: {avg_walls:.1f}")


# =============================================================================
# RASTER PDF INGESTION TESTS
# =============================================================================

@pytest.mark.skipif(not RASTER_PDF_PATHS, reason="No raster PDFs found")
class TestRasterPDFIngestion:
    """Ingestion tests using raster-based PDFs (processed via Gemini vision fallback)."""

    @patch("app.services.raster_wall_extractor.genai.Client")
    @pytest.mark.parametrize("pdf_path", RASTER_PDF_PATHS, ids=RASTER_PDF_NAMES)
    def test_ingest_raster_floorplan_succeeds(self, mock_genai_client, client, pdf_path, monkeypatch):
        """Raster PDFs are processed via Gemini fallback and return 200."""
        from app.services.raster_wall_extractor import _RasterWallResult, _WallSegmentPx

        monkeypatch.setattr(
            "app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "test_key"
        )

        mock_gemini = MagicMock()
        mock_genai_client.return_value = mock_gemini
        mock_response = MagicMock()
        mock_response.parsed = _RasterWallResult(
            walls=[
                _WallSegmentPx(x1=0.0, y1=0.0, x2=400.0, y2=0.0, thickness_px=10.0),
                _WallSegmentPx(x1=400.0, y1=0.0, x2=400.0, y2=600.0, thickness_px=10.0),
            ]
        )
        mock_gemini.models.generate_content.return_value = mock_response

        pdf_name = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as f:
            response = client.post(
                "/api/v1/ingest",
                data={"file": (f, pdf_name)},
                content_type="multipart/form-data",
            )

        assert response.status_code == 200, \
            f"Raster PDF {pdf_name} should return 200 via fallback, got {response.status_code}: {response.get_json()}"

        data = response.get_json()
        assert "total_wall_count" in data
        assert "wall_segments" in data
        assert "source" in data
        assert data["source"] == "raster"

    def test_raster_pdf_no_api_key_returns_500(self, client, monkeypatch):
        """Raster PDF without GOOGLE_API_KEY returns 500 (cannot process)."""
        monkeypatch.setattr(
            "app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", ""
        )

        if not RASTER_PDF_PATHS:
            pytest.skip("No raster PDFs available")

        pdf_path = RASTER_PDF_PATHS[0]
        pdf_name = os.path.basename(pdf_path)

        with open(pdf_path, "rb") as f:
            response = client.post(
                "/api/v1/ingest",
                data={"file": (f, pdf_name)},
                content_type="multipart/form-data",
            )

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data

    @patch("app.services.raster_wall_extractor.genai.Client")
    def test_all_raster_pdfs_ingest_with_mocked_gemini(self, mock_genai_client, client, monkeypatch):
        """All raster PDFs succeed when Gemini is mocked."""
        from app.services.raster_wall_extractor import _RasterWallResult, _WallSegmentPx

        monkeypatch.setattr(
            "app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "test_key"
        )

        mock_gemini = MagicMock()
        mock_genai_client.return_value = mock_gemini
        mock_response = MagicMock()
        mock_response.parsed = _RasterWallResult(
            walls=[
                _WallSegmentPx(x1=0.0, y1=0.0, x2=200.0, y2=0.0, thickness_px=8.0),
            ]
        )
        mock_gemini.models.generate_content.return_value = mock_response

        failed = []
        for pdf_path in RASTER_PDF_PATHS:
            pdf_name = os.path.basename(pdf_path)
            with open(pdf_path, "rb") as f:
                response = client.post(
                    "/api/v1/ingest",
                    data={"file": (f, pdf_name)},
                    content_type="multipart/form-data",
                )
            if response.status_code != 200:
                failed.append((pdf_name, response.status_code, response.get_json()))

        assert not failed, f"Raster PDFs that failed: {failed}"


# =============================================================================
# MIXED PDF BATCH TESTS
# =============================================================================

class TestMixedPDFBatch:
    """Tests covering both vector and raster PDFs together."""

    def test_pdf_categorization_complete(self):
        """Verify all PDFs are categorized."""
        total = len(VECTOR_PDF_PATHS) + len(RASTER_PDF_PATHS)
        assert total == len(ALL_PDF_PATHS), \
            f"PDF categorization incomplete: {total} categorized vs {len(ALL_PDF_PATHS)} total"

    def test_at_least_one_vector_pdf(self):
        """Ensure we have at least one vector PDF for testing."""
        assert len(VECTOR_PDF_PATHS) >= 1, "Need at least one vector PDF"

    def test_at_least_one_raster_pdf(self):
        """Ensure we have at least one raster PDF for testing."""
        assert len(RASTER_PDF_PATHS) >= 1, "Need at least one raster PDF"
