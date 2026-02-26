"""Tests for the raster wall extractor service."""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.models.geometry import WallDetectionResult, WallSegment
from app.services.raster_wall_extractor import (
    extract_walls_from_raster,
    _convert_to_wall_segments,
    _WallSegmentPx,
    _RasterWallResult,
    _RASTER_SCALE,
)


# ---------------------------------------------------------------------------
# Unit tests (fully mocked)
# ---------------------------------------------------------------------------

@patch("app.services.raster_wall_extractor.genai.Client")
@patch("app.services.raster_wall_extractor.fitz.open")
def test_extract_walls_from_raster_success(mock_fitz_open, mock_genai_client, monkeypatch):
    """Happy path: Gemini returns valid wall segments."""
    monkeypatch.setattr("app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "test_key")

    # Mock PDF rasterization
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.rect.width = 612.0
    mock_page.rect.height = 792.0
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"fake_png_bytes"
    mock_page.get_pixmap.return_value = mock_pixmap
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    mock_fitz_open.return_value = mock_doc

    # Mock Gemini response — pixel coords (2x scale, so divide by 2.0 for PDF pts)
    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client

    gemini_result = _RasterWallResult(
        walls=[
            _WallSegmentPx(x1=0.0, y1=0.0, x2=200.0, y2=0.0, thickness_px=10.0),
            _WallSegmentPx(x1=200.0, y1=0.0, x2=200.0, y2=400.0, thickness_px=10.0),
        ]
    )
    mock_response = MagicMock()
    mock_response.parsed = gemini_result
    mock_client.models.generate_content.return_value = mock_response

    result = extract_walls_from_raster("fake.pdf")

    assert isinstance(result, WallDetectionResult)
    assert result.source == "raster"
    assert result.total_wall_count == 2
    assert len(result.wall_segments) == 2

    # Coordinates converted: pixel / 2.0 = PDF points
    seg0 = result.wall_segments[0]
    assert seg0.x1 == pytest.approx(0.0)
    assert seg0.x2 == pytest.approx(100.0)  # 200px / 2.0
    assert seg0.thickness == pytest.approx(5.0)  # 10px / 2.0

    assert result.total_linear_pts == pytest.approx(
        sum(s.length_pts for s in result.wall_segments)
    )


def test_extract_walls_from_raster_no_api_key(monkeypatch):
    """Missing GOOGLE_API_KEY raises RuntimeError."""
    monkeypatch.setattr("app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "")

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        extract_walls_from_raster("fake.pdf")


@patch("app.services.raster_wall_extractor.fitz.open")
def test_extract_walls_from_raster_bad_pdf(mock_fitz_open, monkeypatch):
    """Corrupted PDF raises ValueError."""
    monkeypatch.setattr("app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "test_key")
    mock_fitz_open.side_effect = Exception("Corrupted PDF")

    with pytest.raises(ValueError, match="Failed to rasterize PDF page"):
        extract_walls_from_raster("fake.pdf")


@patch("app.services.raster_wall_extractor.genai.Client")
@patch("app.services.raster_wall_extractor.fitz.open")
def test_extract_walls_from_raster_gemini_failure(mock_fitz_open, mock_genai_client, monkeypatch):
    """Gemini API failure raises RuntimeError."""
    monkeypatch.setattr("app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "test_key")

    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"fake_png_bytes"
    mock_page.get_pixmap.return_value = mock_pixmap
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    mock_fitz_open.return_value = mock_doc

    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client
    mock_client.models.generate_content.side_effect = Exception("API timeout")

    with pytest.raises(RuntimeError, match="Gemini vision call failed"):
        extract_walls_from_raster("fake.pdf")


@patch("app.services.raster_wall_extractor.genai.Client")
@patch("app.services.raster_wall_extractor.fitz.open")
def test_extract_walls_from_raster_empty_response(mock_fitz_open, mock_genai_client, monkeypatch):
    """Gemini returns no walls — result is valid but empty."""
    monkeypatch.setattr("app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "test_key")

    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"fake_png_bytes"
    mock_page.get_pixmap.return_value = mock_pixmap
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    mock_fitz_open.return_value = mock_doc

    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.parsed = _RasterWallResult(walls=[])
    mock_client.models.generate_content.return_value = mock_response

    result = extract_walls_from_raster("fake.pdf")

    assert isinstance(result, WallDetectionResult)
    assert result.source == "raster"
    assert result.total_wall_count == 0
    assert result.wall_segments == []


@patch("app.services.raster_wall_extractor.genai.Client")
@patch("app.services.raster_wall_extractor.fitz.open")
def test_extract_walls_from_raster_none_parsed(mock_fitz_open, mock_genai_client, monkeypatch):
    """Gemini returns None parsed result — treated as empty."""
    monkeypatch.setattr("app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "test_key")

    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"fake_png_bytes"
    mock_page.get_pixmap.return_value = mock_pixmap
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    mock_fitz_open.return_value = mock_doc

    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_client.models.generate_content.return_value = mock_response

    result = extract_walls_from_raster("fake.pdf")
    assert result.total_wall_count == 0


@patch("app.services.raster_wall_extractor.fitz.open")
def test_extract_walls_from_raster_invalid_page(mock_fitz_open, monkeypatch):
    """Requesting a page beyond the document length raises ValueError."""
    monkeypatch.setattr("app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "test_key")

    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 1
    mock_fitz_open.return_value = mock_doc

    with pytest.raises(ValueError, match="Page 5 not found"):
        extract_walls_from_raster("fake.pdf", page_num=5)


# ---------------------------------------------------------------------------
# Unit tests for _convert_to_wall_segments helper
# ---------------------------------------------------------------------------

def test_convert_to_wall_segments_basic():
    """Pixel coordinates are divided by scale and converted to WallSegments."""
    px_walls = [
        _WallSegmentPx(x1=0.0, y1=0.0, x2=100.0, y2=0.0, thickness_px=8.0),
    ]
    segments = _convert_to_wall_segments(px_walls, scale=2.0)

    assert len(segments) == 1
    seg = segments[0]
    assert seg.x1 == pytest.approx(0.0)
    assert seg.x2 == pytest.approx(50.0)
    assert seg.thickness == pytest.approx(4.0)
    assert seg.length_pts == pytest.approx(50.0)


def test_convert_to_wall_segments_direction_standardized():
    """Direction is standardized so x1 <= x2 (left-to-right)."""
    px_walls = [
        _WallSegmentPx(x1=200.0, y1=0.0, x2=0.0, y2=0.0, thickness_px=6.0),
    ]
    segments = _convert_to_wall_segments(px_walls, scale=2.0)

    assert segments[0].x1 <= segments[0].x2


def test_convert_to_wall_segments_skips_degenerate():
    """Zero-length segments (dots) are skipped."""
    px_walls = [
        _WallSegmentPx(x1=10.0, y1=10.0, x2=10.0, y2=10.0, thickness_px=5.0),
    ]
    segments = _convert_to_wall_segments(px_walls, scale=2.0)
    assert len(segments) == 0


def test_convert_to_wall_segments_multiple():
    """Multiple walls are all converted."""
    px_walls = [
        _WallSegmentPx(x1=0.0, y1=0.0, x2=100.0, y2=0.0, thickness_px=10.0),
        _WallSegmentPx(x1=100.0, y1=0.0, x2=100.0, y2=200.0, thickness_px=10.0),
        _WallSegmentPx(x1=0.0, y1=200.0, x2=100.0, y2=200.0, thickness_px=10.0),
        _WallSegmentPx(x1=0.0, y1=0.0, x2=0.0, y2=200.0, thickness_px=10.0),
    ]
    segments = _convert_to_wall_segments(px_walls, scale=2.0)
    assert len(segments) == 4


# ---------------------------------------------------------------------------
# Integration tests with real sample PDFs (mocked Gemini)
# ---------------------------------------------------------------------------

SAMPLE_PDFS_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_pdfs")


def _get_raster_pdfs():
    import fitz
    paths = []
    for f in os.listdir(SAMPLE_PDFS_DIR):
        if not f.endswith(".pdf"):
            continue
        full = os.path.join(SAMPLE_PDFS_DIR, f)
        try:
            doc = fitz.open(full)
            if len(doc[0].get_drawings()) == 0:
                paths.append(full)
            doc.close()
        except Exception:
            pass
    return paths


RASTER_PDF_PATHS = _get_raster_pdfs()
RASTER_PDF_NAMES = [os.path.basename(p) for p in RASTER_PDF_PATHS]


@pytest.mark.skipif(not RASTER_PDF_PATHS, reason="No raster PDFs found in sample_pdfs/")
class TestRasterPDFExtraction:
    """Integration tests using real raster PDFs with mocked Gemini."""

    @patch("app.services.raster_wall_extractor.genai.Client")
    @pytest.mark.parametrize("pdf_path", RASTER_PDF_PATHS, ids=RASTER_PDF_NAMES)
    def test_raster_pdf_extracts_successfully(self, mock_genai_client, pdf_path, monkeypatch):
        """Real raster PDFs can be processed end-to-end (mocked Gemini)."""
        monkeypatch.setattr(
            "app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "test_key"
        )

        mock_client = MagicMock()
        mock_genai_client.return_value = mock_client

        gemini_result = _RasterWallResult(
            walls=[
                _WallSegmentPx(x1=0.0, y1=0.0, x2=400.0, y2=0.0, thickness_px=10.0),
                _WallSegmentPx(x1=400.0, y1=0.0, x2=400.0, y2=600.0, thickness_px=10.0),
            ]
        )
        mock_response = MagicMock()
        mock_response.parsed = gemini_result
        mock_client.models.generate_content.return_value = mock_response

        result = extract_walls_from_raster(pdf_path)

        assert isinstance(result, WallDetectionResult)
        assert result.source == "raster"
        assert result.total_wall_count == 2
        assert mock_client.models.generate_content.called

    @patch("app.services.raster_wall_extractor.genai.Client")
    def test_all_raster_pdfs_can_be_rasterized(self, mock_genai_client, monkeypatch):
        """All raster PDFs can be opened and converted to PNG without errors."""
        import fitz

        monkeypatch.setattr(
            "app.services.raster_wall_extractor.settings.GOOGLE_API_KEY", "test_key"
        )

        mock_client = MagicMock()
        mock_genai_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.parsed = _RasterWallResult(walls=[])
        mock_client.models.generate_content.return_value = mock_response

        failed = []
        for pdf_path in RASTER_PDF_PATHS:
            try:
                doc = fitz.open(pdf_path)
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(_RASTER_SCALE, _RASTER_SCALE))
                assert pix.width > 0
                assert pix.height > 0
                doc.close()
            except Exception as exc:
                failed.append((os.path.basename(pdf_path), str(exc)))

        assert not failed, f"PDFs that failed rasterization: {failed}"
