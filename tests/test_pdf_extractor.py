"""Tests for PDF vector extraction."""

import os
import pytest
import fitz  # PyMuPDF

from app.services.pdf_extractor import extract_vectors, extract_summary
from app.models.geometry import VectorLine, ExtractionResult
from tests.conftest import (
    get_categorized_pdf_paths,
    categorize_pdf as _categorize_pdf,
)


# ---------------------------------------------------------------------------
# Lazy PDF discovery — uses conftest helpers, safe when directories absent.
# Categorization runs once at collection time via guarded helpers.
# ---------------------------------------------------------------------------

ALL_PDF_PATHS, VECTOR_PDF_PATHS, RASTER_PDF_PATHS = get_categorized_pdf_paths()
ALL_PDF_NAMES = [os.path.basename(p) for p in ALL_PDF_PATHS]
VECTOR_PDF_NAMES = [os.path.basename(p) for p in VECTOR_PDF_PATHS]
RASTER_PDF_NAMES = [os.path.basename(p) for p in RASTER_PDF_PATHS]


def categorize_pdf(pdf_path: str) -> str:
    """Delegate to shared conftest categorizer."""
    return _categorize_pdf(pdf_path)


class TestExtractVectors:
    """Tests for the extract_vectors function."""

    @pytest.fixture
    def sample_pdf_path(self, tmp_path):
        """Create a simple test PDF with vector lines."""
        pdf_path = tmp_path / "test_drawing.pdf"

        # Create a simple PDF with some vector drawings
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)  # Letter size

        # Draw a rectangle (wall-like)
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(100, 100, 500, 600))
        shape.finish(width=2.0, color=(0, 0, 0))  # Thick black line
        shape.commit()

        # Draw some lines (dimension-like, thinner)
        shape = page.new_shape()
        shape.draw_line(fitz.Point(50, 50), fitz.Point(550, 50))
        shape.finish(width=0.5, color=(0.5, 0.5, 0.5))  # Thin gray line
        shape.commit()

        doc.save(str(pdf_path))
        doc.close()

        return str(pdf_path)

    def test_extract_vectors_returns_result(self, sample_pdf_path):
        """Test that extract_vectors returns an ExtractionResult."""
        result = extract_vectors(sample_pdf_path)

        assert isinstance(result, ExtractionResult)
        assert result.page_width == 612
        assert result.page_height == 792

    def test_extract_vectors_returns_lines(self, sample_pdf_path):
        """Test that lines are extracted from the PDF."""
        result = extract_vectors(sample_pdf_path)

        # Should have lines from rectangle (4) + line (1) = 5 lines
        assert len(result.lines) > 0

        # Check that all items are VectorLine objects
        for line in result.lines:
            assert isinstance(line, VectorLine)
            assert line.width >= 0

    def test_extract_vectors_has_coordinates(self, sample_pdf_path):
        """Test that extracted lines have valid coordinates."""
        result = extract_vectors(sample_pdf_path)

        for line in result.lines:
            # Coordinates should be valid numbers
            assert isinstance(line.x1, (int, float))
            assert isinstance(line.y1, (int, float))
            assert isinstance(line.x2, (int, float))
            assert isinstance(line.y2, (int, float))

            # Width should be positive
            assert line.width >= 0

    def test_extract_vectors_captures_width(self, sample_pdf_path):
        """Test that line widths are captured correctly."""
        result = extract_vectors(sample_pdf_path)

        # Should capture both thick (2.0) and thin (0.5) lines
        widths = result.get_unique_widths()
        assert len(widths) >= 1

        # At least one line should have width > 0
        assert any(line.width > 0 for line in result.lines)

    def test_extract_vectors_captures_color(self, sample_pdf_path):
        """Test that line colors are captured."""
        result = extract_vectors(sample_pdf_path)

        # Some lines should have color info
        lines_with_color = [l for l in result.lines if l.color is not None]
        assert len(lines_with_color) > 0

    def test_extract_vectors_metadata(self, sample_pdf_path):
        """Test that metadata is populated."""
        result = extract_vectors(sample_pdf_path)

        assert result.metadata["page_number"] == 1
        assert result.metadata["total_pages"] == 1

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises((FileNotFoundError, fitz.FileNotFoundError)):
            extract_vectors("/nonexistent/file.pdf")

    def test_invalid_page_number(self, sample_pdf_path):
        """Test that invalid page number raises ValueError."""
        with pytest.raises(ValueError):
            extract_vectors(sample_pdf_path, page_num=99)


class TestExtractionResult:
    """Tests for ExtractionResult methods."""

    def test_get_line_count(self):
        """Test get_line_count method."""
        lines = [
            VectorLine(x1=0, y1=0, x2=10, y2=0, width=1.0),
            VectorLine(x1=10, y1=0, x2=10, y2=10, width=1.0),
        ]
        result = ExtractionResult(lines=lines, page_width=100, page_height=100)

        assert result.get_line_count() == 2

    def test_get_unique_widths(self):
        """Test get_unique_widths method."""
        lines = [
            VectorLine(x1=0, y1=0, x2=10, y2=0, width=1.0),
            VectorLine(x1=10, y1=0, x2=10, y2=10, width=2.0),
            VectorLine(x1=10, y1=10, x2=0, y2=10, width=1.0),  # Same width as first
        ]
        result = ExtractionResult(lines=lines, page_width=100, page_height=100)

        widths = result.get_unique_widths()
        assert len(widths) == 2
        assert 1.0 in widths
        assert 2.0 in widths

    def test_get_bounding_box(self):
        """Test get_bounding_box method."""
        lines = [
            VectorLine(x1=10, y1=10, x2=50, y2=10, width=1.0),
            VectorLine(x1=50, y1=10, x2=50, y2=60, width=1.0),
        ]
        result = ExtractionResult(lines=lines, page_width=100, page_height=100)

        bbox = result.get_bounding_box()
        assert bbox == (10, 10, 50, 60)

    def test_vector_line_length(self):
        """Test VectorLine.length method."""
        line = VectorLine(x1=0, y1=0, x2=3, y2=4, width=1.0)  # 3-4-5 triangle
        assert line.length() == 5.0

    def test_vector_line_is_horizontal(self):
        """Test VectorLine.is_horizontal method."""
        horizontal = VectorLine(x1=0, y1=10, x2=100, y2=10, width=1.0)
        vertical = VectorLine(x1=10, y1=0, x2=10, y2=100, width=1.0)

        assert horizontal.is_horizontal()
        assert not vertical.is_horizontal()

    def test_vector_line_is_vertical(self):
        """Test VectorLine.is_vertical method."""
        horizontal = VectorLine(x1=0, y1=10, x2=100, y2=10, width=1.0)
        vertical = VectorLine(x1=10, y1=0, x2=10, y2=100, width=1.0)

        assert not horizontal.is_vertical()
        assert vertical.is_vertical()


class TestExtractSummary:
    """Tests for the extract_summary function."""

    @pytest.fixture
    def sample_pdf_path(self, tmp_path):
        """Create a simple test PDF."""
        pdf_path = tmp_path / "test_summary.pdf"

        doc = fitz.open()
        page = doc.new_page(width=612, height=792)

        # Draw a rectangle
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(100, 100, 500, 600))
        shape.finish(width=2.0)
        shape.commit()

        doc.save(str(pdf_path))
        doc.close()

        return str(pdf_path)

    def test_extract_summary_structure(self, sample_pdf_path):
        """Test that extract_summary returns expected structure."""
        summary = extract_summary(sample_pdf_path)

        assert "total_lines" in summary
        assert "page_dimensions" in summary
        assert "bounding_box" in summary
        assert "unique_line_widths" in summary
        assert "width_count" in summary

        assert summary["total_lines"] > 0
        assert len(summary["page_dimensions"]) == 2


# =============================================================================
# VECTOR FLOORPLAN PDF TESTS
# =============================================================================

@pytest.mark.skipif(not VECTOR_PDF_PATHS, reason="No vector PDFs found")
class TestVectorFloorplanPDFs:
    """Tests using vector-based floorplan PDFs (have drawings)."""

    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_extract_vectors_vector_pdf(self, pdf_path):
        """Test that extract_vectors works on vector floorplan PDFs."""
        result = extract_vectors(pdf_path)

        assert isinstance(result, ExtractionResult)
        assert result.page_width > 0
        assert result.page_height > 0
        assert len(result.lines) > 0  # Vector PDFs should have lines

    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_extract_vectors_line_quality_vector_pdf(self, pdf_path):
        """Test that extracted lines from vector PDFs have valid properties."""
        result = extract_vectors(pdf_path)

        for line in result.lines:
            # All coordinates should be finite numbers
            assert isinstance(line.x1, (int, float))
            assert isinstance(line.y1, (int, float))
            assert isinstance(line.x2, (int, float))
            assert isinstance(line.y2, (int, float))
            assert not (line.x1 != line.x1)  # Check for NaN
            assert not (line.y1 != line.y1)
            assert not (line.x2 != line.x2)
            assert not (line.y2 != line.y2)

            # Width should be non-negative
            assert line.width >= 0

    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_extract_summary_vector_pdf(self, pdf_path):
        """Test extract_summary on vector floorplan PDFs."""
        summary = extract_summary(pdf_path)

        assert summary["total_lines"] > 0
        assert len(summary["page_dimensions"]) == 2
        assert summary["page_dimensions"][0] > 0  # width
        assert summary["page_dimensions"][1] > 0  # height

        # Should have some line widths detected
        assert len(summary["unique_line_widths"]) > 0
        assert summary["width_count"] > 0

    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_bounding_box_vector_pdf(self, pdf_path):
        """Test bounding box calculation on vector floorplan PDFs."""
        result = extract_vectors(pdf_path)
        bbox = result.get_bounding_box()

        assert bbox is not None
        x1, y1, x2, y2 = bbox

        # Bounding box should be within page bounds
        assert x1 >= 0
        assert y1 >= 0
        assert x2 <= result.page_width
        assert y2 <= result.page_height

        # Bounding box should have positive dimensions
        assert x2 > x1
        assert y2 > y1

    def test_all_vector_pdfs_have_vectors(self):
        """Verify all vector PDFs contain extractable vector graphics."""
        failed_pdfs = []

        for pdf_path in VECTOR_PDF_PATHS:
            result = extract_vectors(pdf_path)
            if len(result.lines) == 0:
                failed_pdfs.append(os.path.basename(pdf_path))

        assert not failed_pdfs, f"Vector PDFs with no vectors: {failed_pdfs}"


# =============================================================================
# RASTER (SCANNED) PDF TESTS
# =============================================================================

@pytest.mark.skipif(not RASTER_PDF_PATHS, reason="No raster PDFs found")
class TestRasterFloorplanPDFs:
    """Tests using raster-based floorplan PDFs (images only, no vectors)."""

    @pytest.mark.parametrize("pdf_path", RASTER_PDF_PATHS, ids=RASTER_PDF_NAMES)
    def test_extract_vectors_raster_pdf_returns_empty(self, pdf_path):
        """Test that raster PDFs return empty extraction (no vectors)."""
        result = extract_vectors(pdf_path)

        assert isinstance(result, ExtractionResult)
        assert result.page_width > 0
        assert result.page_height > 0
        assert len(result.lines) == 0  # Raster PDFs have no vector lines

    @pytest.mark.parametrize("pdf_path", RASTER_PDF_PATHS, ids=RASTER_PDF_NAMES)
    def test_extract_summary_raster_pdf(self, pdf_path):
        """Test extract_summary on raster PDFs."""
        summary = extract_summary(pdf_path)

        # Should have page dimensions but no lines
        assert summary["total_lines"] == 0
        assert len(summary["page_dimensions"]) == 2
        assert summary["page_dimensions"][0] > 0
        assert summary["page_dimensions"][1] > 0

    def test_all_raster_pdfs_are_scanned(self):
        """Verify all raster PDFs have zero vectors (as expected)."""
        vector_found = []

        for pdf_path in RASTER_PDF_PATHS:
            result = extract_vectors(pdf_path)
            if len(result.lines) > 0:
                vector_found.append(os.path.basename(pdf_path))

        assert not vector_found, f"Raster PDFs unexpectedly had vectors: {vector_found}"

    def test_raster_pdf_page_dimensions(self):
        """Test that all raster PDFs have valid page dimensions."""
        for pdf_path in RASTER_PDF_PATHS:
            result = extract_vectors(pdf_path)

            assert result.page_width > 0, f"Invalid width in {os.path.basename(pdf_path)}"
            assert result.page_height > 0, f"Invalid height in {os.path.basename(pdf_path)}"

    def test_raster_pdf_summary_consistency(self):
        """Test consistency of raster PDF summaries."""
        summaries = []

        for pdf_path in RASTER_PDF_PATHS:
            summary = extract_summary(pdf_path)
            summaries.append({
                "name": os.path.basename(pdf_path),
                "lines": summary["total_lines"],
                "width": summary["page_dimensions"][0],
                "height": summary["page_dimensions"][1],
            })

        # All should have 0 lines
        for s in summaries:
            assert s["lines"] == 0, f"{s['name']} should have 0 lines"

        # Log dimensions for debugging
        print(f"\nRaster PDF dimensions:")
        for s in summaries[:5]:  # Show first 5
            print(f"  {s['name']}: {s['width']:.1f} x {s['height']:.1f}")
        if len(summaries) > 5:
            print(f"  ... and {len(summaries) - 5} more")


# =============================================================================
# PDF CATEGORIZATION TESTS
# =============================================================================

class TestPDFCategorization:
    """Tests for PDF type categorization."""

    def test_at_least_one_vector_pdf_exists(self):
        """Ensure we have at least one vector PDF for testing."""
        assert len(VECTOR_PDF_PATHS) >= 1, "Need at least one vector PDF"

    def test_raster_pdfs_available(self):
        """Ensure we have raster PDFs for testing."""
        assert len(RASTER_PDF_PATHS) >= 1, "Need at least one raster PDF"

    def test_categorization_accuracy(self):
        """Verify PDF categorization is accurate."""
        for pdf_path in ALL_PDF_PATHS:
            category = categorize_pdf(pdf_path)
            assert category in ["vector", "raster", "empty", "error"]

    def test_all_pdfs_categorized(self):
        """Verify all PDFs are categorized."""
        total_categorized = len(VECTOR_PDF_PATHS) + len(RASTER_PDF_PATHS)
        assert total_categorized == len(ALL_PDF_PATHS), \
            f"Mismatch: {total_categorized} categorized vs {len(ALL_PDF_PATHS)} total"
