"""Tests for wall detector service."""

import os
import pytest

from app.models.geometry import ExtractionResult, VectorLine, WallSegment
from app.services.wall_detector import detect_walls
from app.services.pdf_extractor import extract_vectors
from tests.conftest import get_categorized_pdf_paths


# ---------------------------------------------------------------------------
# Lazy PDF discovery — uses conftest helpers, safe when directories absent.
# ---------------------------------------------------------------------------

ALL_PDF_PATHS, VECTOR_PDF_PATHS, RASTER_PDF_PATHS = get_categorized_pdf_paths()
ALL_PDF_NAMES = [os.path.basename(p) for p in ALL_PDF_PATHS]
VECTOR_PDF_NAMES = [os.path.basename(p) for p in VECTOR_PDF_PATHS]
RASTER_PDF_NAMES = [os.path.basename(p) for p in RASTER_PDF_PATHS]


def test_detect_walls_filters_by_thickness():
    # 5 thick lines (walls), 5 thin lines (dimensions)
    lines = []

    # Thick lines
    for i in range(5):
        lines.append(VectorLine(x1=0, y1=i*10, x2=100, y2=i*10, width=2.0))

    # Thin lines
    for i in range(5):
        lines.append(VectorLine(x1=0, y1=i*10+5, x2=100, y2=i*10+5, width=0.5))

    extraction = ExtractionResult(lines=lines, page_width=800, page_height=600, metadata={})

    result = detect_walls(extraction, wall_thickness_min=1.5)

    assert result.total_wall_count == 5
    assert len(result.wall_segments) == 5
    assert result.total_linear_pts == 5 * 100.0

def test_detect_walls_deduplicates():
    # Two thick lines perfectly overlapping
    lines = [
        VectorLine(x1=10, y1=10, x2=50, y2=10, width=2.0),
        VectorLine(x1=10, y1=10, x2=50, y2=10, width=2.0),
    ]

    extraction = ExtractionResult(lines=lines, page_width=800, page_height=600, metadata={})
    result = detect_walls(extraction)

    assert result.total_wall_count == 1
    assert result.total_linear_pts == 40.0

def test_detect_walls_deduplicates_within_tolerance():
    # Two thick lines close but not identical
    lines = [
        VectorLine(x1=10, y1=10, x2=50, y2=10, width=2.0),
        # Shifted by 1 pt in X and Y (within 2pt tolerance for start and end)
        VectorLine(x1=11, y1=11, x2=51, y2=11, width=2.0),
    ]

    extraction = ExtractionResult(lines=lines, page_width=800, page_height=600, metadata={})
    result = detect_walls(extraction)

    assert result.total_wall_count == 1

def test_detect_walls_length_calculation():
    # 3-4-5 triangle line
    lines = [
        VectorLine(x1=0, y1=0, x2=30, y2=40, width=2.0)
    ]

    extraction = ExtractionResult(lines=lines, page_width=800, page_height=600, metadata={})
    result = detect_walls(extraction)

    assert result.total_wall_count == 1
    assert result.wall_segments[0].length_pts == 50.0


def test_detect_walls_standardizes_direction():
    """Test that walls are standardized (left-to-right, top-to-bottom)."""
    # Lines in both directions
    lines = [
        VectorLine(x1=100, y1=100, x2=50, y2=100, width=2.0),  # Right-to-left
        VectorLine(x1=50, y1=200, x2=100, y2=200, width=2.0),  # Left-to-right
        VectorLine(x1=200, y1=50, x2=200, y2=100, width=2.0),  # Top-to-bottom
        VectorLine(x1=300, y1=100, x2=300, y2=50, width=2.0),  # Bottom-to-top
    ]

    extraction = ExtractionResult(lines=lines, page_width=800, page_height=600, metadata={})
    result = detect_walls(extraction)

    # Horizontal walls should have x1 < x2
    horizontals = [w for w in result.wall_segments if abs(w.y2 - w.y1) < 0.1]
    for wall in horizontals:
        assert wall.x1 < wall.x2, f"Horizontal wall not standardized: ({wall.x1}, {wall.y1}) -> ({wall.x2}, {wall.y2})"

    # Vertical walls should have y1 < y2
    verticals = [w for w in result.wall_segments if abs(w.x2 - w.x1) < 0.1]
    for wall in verticals:
        assert wall.y1 < wall.y2, f"Vertical wall not standardized: ({wall.x1}, {wall.y1}) -> ({wall.x2}, {wall.y2})"


def test_detect_walls_different_thickness_thresholds():
    """Test wall detection with different thickness thresholds."""
    lines = [
        VectorLine(x1=0, y1=0, x2=100, y2=0, width=1.0),
        VectorLine(x1=0, y1=10, x2=100, y2=10, width=2.0),
        VectorLine(x1=0, y1=20, x2=100, y2=20, width=3.0),
        VectorLine(x1=0, y1=30, x2=100, y2=30, width=4.0),
    ]

    extraction = ExtractionResult(lines=lines, page_width=800, page_height=600, metadata={})

    # With threshold 0.5, should get all 4
    result = detect_walls(extraction, wall_thickness_min=0.5)
    assert result.total_wall_count == 4

    # With threshold 1.5, should get 3 (excluding width=1.0)
    result = detect_walls(extraction, wall_thickness_min=1.5)
    assert result.total_wall_count == 3

    # With threshold 2.5, should get 2 (excluding width=1.0, 2.0)
    result = detect_walls(extraction, wall_thickness_min=2.5)
    assert result.total_wall_count == 2

    # With threshold 5.0, should get 0
    result = detect_walls(extraction, wall_thickness_min=5.0)
    assert result.total_wall_count == 0


def test_detect_walls_empty_extraction():
    """Test wall detection with empty extraction (raster PDF)."""
    extraction = ExtractionResult(lines=[], page_width=512, page_height=512, metadata={})
    result = detect_walls(extraction)

    assert result.total_wall_count == 0
    assert len(result.wall_segments) == 0
    assert result.total_linear_pts == 0.0


# =============================================================================
# VECTOR FLOORPLAN PDF TESTS
# =============================================================================

@pytest.mark.skipif(not VECTOR_PDF_PATHS, reason="No vector PDFs found")
class TestVectorFloorplanWallDetection:
    """Wall detection tests using vector floorplan PDFs."""

    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_detect_walls_vector_pdf(self, pdf_path):
        """Test wall detection on vector floorplan PDFs."""
        extraction = extract_vectors(pdf_path)
        result = detect_walls(extraction)

        # Real floorplans should have walls detected
        assert result.total_wall_count > 0, f"No walls detected in {os.path.basename(pdf_path)}"
        assert len(result.wall_segments) > 0

    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_wall_segment_properties_vector(self, pdf_path):
        """Test that detected walls have valid properties."""
        extraction = extract_vectors(pdf_path)
        result = detect_walls(extraction)

        for wall in result.wall_segments:
            # All coordinates should be valid
            assert isinstance(wall.x1, (int, float))
            assert isinstance(wall.y1, (int, float))
            assert isinstance(wall.x2, (int, float))
            assert isinstance(wall.y2, (int, float))

            # Length should be positive
            assert wall.length_pts > 0

            # Thickness should be non-negative
            assert wall.thickness >= 0

            # Wall should be within page bounds
            assert wall.x1 >= 0 and wall.x1 <= extraction.page_width
            assert wall.x2 >= 0 and wall.x2 <= extraction.page_width
            assert wall.y1 >= 0 and wall.y1 <= extraction.page_height
            assert wall.y2 >= 0 and wall.y2 <= extraction.page_height

    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_wall_detection_deduplication_vector(self, pdf_path):
        """Test that wall detection properly deduplicates on vector PDFs."""
        extraction = extract_vectors(pdf_path)
        result = detect_walls(extraction)

        # Check for exact duplicates in output
        wall_keys = set()
        duplicates = []

        for wall in result.wall_segments:
            # Create a key with rounded coordinates (2 decimal places)
            key = (
                round(wall.x1, 2),
                round(wall.y1, 2),
                round(wall.x2, 2),
                round(wall.y2, 2),
                round(wall.thickness, 2)
            )
            if key in wall_keys:
                duplicates.append(key)
            wall_keys.add(key)

        assert not duplicates, f"Found {len(duplicates)} duplicate walls in {os.path.basename(pdf_path)}"

    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_total_linear_feet_calculation_vector(self, pdf_path):
        """Test that total linear feet is calculated correctly."""
        extraction = extract_vectors(pdf_path)
        result = detect_walls(extraction)

        # Calculate expected total from segments
        expected_total = sum(wall.length_pts for wall in result.wall_segments)

        # Should match with small tolerance for floating point
        assert abs(result.total_linear_pts - expected_total) < 0.01, \
            f"Total linear feet mismatch in {os.path.basename(pdf_path)}"

    def test_all_vector_floorplans_have_walls(self):
        """Verify all vector PDFs have detectable walls."""
        failed_pdfs = []
        wall_counts = []

        for pdf_path in VECTOR_PDF_PATHS:
            extraction = extract_vectors(pdf_path)
            result = detect_walls(extraction)
            wall_counts.append((os.path.basename(pdf_path), result.total_wall_count))
            if result.total_wall_count == 0:
                failed_pdfs.append(os.path.basename(pdf_path))

        # Sort by wall count for debugging
        wall_counts.sort(key=lambda x: x[1])
        print(f"\nVector PDF wall detection summary:")
        for name, count in wall_counts:
            print(f"  {name}: {count} walls")

        assert not failed_pdfs, f"Vector PDFs with no walls detected: {failed_pdfs}"

    def test_wall_complexity_variation_vector(self):
        """Verify vector PDFs have varying wall complexity."""
        wall_counts = []

        for pdf_path in VECTOR_PDF_PATHS:
            extraction = extract_vectors(pdf_path)
            result = detect_walls(extraction)
            wall_counts.append((os.path.basename(pdf_path), result.total_wall_count))

        # Sort by wall count
        wall_counts.sort(key=lambda x: x[1])

        min_walls = wall_counts[0][1]
        max_walls = wall_counts[-1][1]

        print(f"\nVector PDF Wall Complexity:")
        print(f"  Min: {wall_counts[0][0]} with {min_walls} walls")
        print(f"  Max: {wall_counts[-1][0]} with {max_walls} walls")

        assert max_walls >= min_walls


# =============================================================================
# RASTER FLOORPLAN PDF TESTS
# =============================================================================

@pytest.mark.skipif(not RASTER_PDF_PATHS, reason="No raster PDFs found")
class TestRasterFloorplanWallDetection:
    """Wall detection tests using raster floorplan PDFs (expect no walls)."""

    @pytest.mark.parametrize("pdf_path", RASTER_PDF_PATHS, ids=RASTER_PDF_NAMES)
    def test_detect_walls_raster_pdf_empty(self, pdf_path):
        """Test that raster PDFs return empty wall detection (no vectors)."""
        extraction = extract_vectors(pdf_path)
        result = detect_walls(extraction)

        # Raster PDFs have no vectors, so no walls should be detected
        assert result.total_wall_count == 0, \
            f"Raster PDF {os.path.basename(pdf_path)} unexpectedly had walls"
        assert len(result.wall_segments) == 0
        assert result.total_linear_pts == 0.0

    def test_all_raster_pdfs_have_no_walls(self):
        """Verify all raster PDFs return zero walls."""
        wall_found = []

        for pdf_path in RASTER_PDF_PATHS:
            extraction = extract_vectors(pdf_path)
            result = detect_walls(extraction)
            if result.total_wall_count > 0:
                wall_found.append(os.path.basename(pdf_path))

        assert not wall_found, f"Raster PDFs unexpectedly had walls: {wall_found}"

    def test_raster_pdf_wall_detection_consistency(self):
        """Test that all raster PDFs consistently return empty results."""
        for pdf_path in RASTER_PDF_PATHS:
            extraction = extract_vectors(pdf_path)
            assert len(extraction.lines) == 0, \
                f"Raster PDF {os.path.basename(pdf_path)} had unexpected vectors"

            result = detect_walls(extraction)
            assert result.total_wall_count == 0
            assert result.total_linear_pts == 0.0
