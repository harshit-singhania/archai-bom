"""Tests for semantic extractor service."""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.models.semantic import SemanticResult, RoomLabel, ScaleInfo
from app.services.semantic_extractor import extract_semantics


# Discover all PDFs in sample_pdfs/
SAMPLE_PDFS_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_pdfs")
ALL_PDF_PATHS = [
    os.path.join(SAMPLE_PDFS_DIR, f) for f in os.listdir(SAMPLE_PDFS_DIR)
    if f.endswith(".pdf") and os.path.isfile(os.path.join(SAMPLE_PDFS_DIR, f))
]
ALL_PDF_NAMES = [os.path.basename(p) for p in ALL_PDF_PATHS]

# Categorize PDFs by type
def categorize_pdf(pdf_path):
    """Check if PDF has vector drawings or raster images."""
    import fitz
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        has_drawings = len(page.get_drawings()) > 0
        doc.close()
        return "vector" if has_drawings else "raster"
    except Exception:
        return "error"

VECTOR_PDF_PATHS = [p for p in ALL_PDF_PATHS if categorize_pdf(p) == "vector"]
RASTER_PDF_PATHS = [p for p in ALL_PDF_PATHS if categorize_pdf(p) == "raster"]
VECTOR_PDF_NAMES = [os.path.basename(p) for p in VECTOR_PDF_PATHS]
RASTER_PDF_NAMES = [os.path.basename(p) for p in RASTER_PDF_PATHS]


@patch("app.services.semantic_extractor.genai.Client")
@patch("app.services.semantic_extractor.fitz.open")
def test_extract_semantics_success(mock_fitz_open, mock_genai_client, monkeypatch):
    """Test successful semantic extraction via mocked Gemini API."""
    # Setup mock config
    monkeypatch.setattr("app.services.semantic_extractor.settings.GOOGLE_API_KEY", "test_key")
    
    # Setup mock PDF
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"fake_image_data"
    mock_page.get_pixmap.return_value = mock_pixmap
    
    # Configure document to return our mock page and have length 1
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    mock_fitz_open.return_value = mock_doc
    
    # Setup mock Gemini response
    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client
    
    mock_response = MagicMock()
    
    expected_result = SemanticResult(
        rooms=[RoomLabel(name="Living Room", approximate_center_x=100.0, approximate_center_y=200.0)],
        scale=ScaleInfo(text="1/4\" = 1'", pixels_per_unit=18.0),
        raw_text=["Not for construction"]
    )
    
    mock_response.parsed = expected_result
    mock_client.models.generate_content.return_value = mock_response
    
    # Execute
    result = extract_semantics("fake_path.pdf")
    
    # Assert
    assert len(result.rooms) == 1
    assert result.rooms[0].name == "Living Room"
    assert result.scale.pixels_per_unit == 18.0
    assert result.raw_text == ["Not for construction"]


def test_extract_semantics_no_api_key(monkeypatch):
    """Test behavior when GOOGLE_API_KEY is not set."""
    monkeypatch.setattr("app.services.semantic_extractor.settings.GOOGLE_API_KEY", "")
    
    result = extract_semantics("fake_path.pdf")
    
    # Should degrade gracefully to empty result
    assert len(result.rooms) == 0
    assert result.scale is None
    assert len(result.raw_text) == 0


@patch("app.services.semantic_extractor.fitz.open")
def test_extract_semantics_invalid_pdf(mock_fitz_open, monkeypatch):
    """Test behavior when PDF processing fails."""
    monkeypatch.setattr("app.services.semantic_extractor.settings.GOOGLE_API_KEY", "test_key")
    
    # Make fitz.open raise an exception
    mock_fitz_open.side_effect = Exception("Corrupted PDF")
    
    result = extract_semantics("fake_path.pdf")
    
    # Should degrade gracefully to empty result
    assert result.rooms == []


# =============================================================================
# REAL PDF TESTS (with mocked Gemini API)
# =============================================================================

@pytest.mark.skipif(not ALL_PDF_PATHS, reason="No sample PDFs found")
class TestRealPDFSemanticExtraction:
    """Semantic extraction tests using real PDFs with mocked Gemini API."""
    
    @patch("app.services.semantic_extractor.genai.Client")
    @pytest.mark.parametrize("pdf_path", ALL_PDF_PATHS, ids=ALL_PDF_NAMES)
    def test_extract_semantics_real_pdf_structure(self, mock_genai_client, pdf_path, monkeypatch):
        """Test that semantic extraction processes real PDFs correctly."""
        monkeypatch.setattr("app.services.semantic_extractor.settings.GOOGLE_API_KEY", "test_key")
        
        # Setup mock Gemini response
        mock_client = MagicMock()
        mock_genai_client.return_value = mock_client
        
        expected_result = SemanticResult(
            rooms=[
                RoomLabel(name="Room 1", approximate_center_x=100.0, approximate_center_y=100.0),
                RoomLabel(name="Room 2", approximate_center_x=200.0, approximate_center_y=200.0),
            ],
            scale=ScaleInfo(text="1/4\" = 1'", pixels_per_unit=18.0),
            raw_text=["Sample text"]
        )
        
        mock_response = MagicMock()
        mock_response.parsed = expected_result
        mock_client.models.generate_content.return_value = mock_response
        
        # Execute
        result = extract_semantics(pdf_path)
        
        # Verify Gemini was called
        assert mock_client.models.generate_content.called
        
        # Verify result structure
        assert isinstance(result, SemanticResult)
        assert len(result.rooms) == 2
        assert result.scale is not None
    
    @pytest.mark.parametrize("pdf_path", ALL_PDF_PATHS, ids=ALL_PDF_NAMES)
    def test_extract_semantics_real_pdf_no_api_key(self, pdf_path, monkeypatch):
        """Test graceful degradation when API key is missing."""
        monkeypatch.setattr("app.services.semantic_extractor.settings.GOOGLE_API_KEY", "")
        
        result = extract_semantics(pdf_path)
        
        # Should return empty result without calling API
        assert isinstance(result, SemanticResult)
        assert len(result.rooms) == 0
        assert result.scale is None
        assert len(result.raw_text) == 0
    
    @patch("app.services.semantic_extractor.genai.Client")
    def test_extract_semantics_all_pdfs_processable(self, mock_genai_client, monkeypatch):
        """Verify all sample PDFs can be processed for semantic extraction."""
        monkeypatch.setattr("app.services.semantic_extractor.settings.GOOGLE_API_KEY", "test_key")
        
        # Setup mock
        mock_client = MagicMock()
        mock_genai_client.return_value = mock_client
        
        expected_result = SemanticResult(
            rooms=[RoomLabel(name="Test Room", approximate_center_x=100.0, approximate_center_y=100.0)],
            scale=ScaleInfo(text="1:100", pixels_per_unit=10.0),
            raw_text=[]
        )
        
        mock_response = MagicMock()
        mock_response.parsed = expected_result
        mock_client.models.generate_content.return_value = mock_response
        
        failed_pdfs = []
        
        for pdf_path in ALL_PDF_PATHS:
            try:
                result = extract_semantics(pdf_path)
                if not isinstance(result, SemanticResult):
                    failed_pdfs.append((os.path.basename(pdf_path), "wrong type"))
            except Exception as e:
                failed_pdfs.append((os.path.basename(pdf_path), str(e)))
        
        assert not failed_pdfs, f"PDFs that failed semantic extraction: {failed_pdfs}"


# =============================================================================
# VECTOR VS RASTER PDF TESTS
# =============================================================================

@pytest.mark.skipif(not VECTOR_PDF_PATHS, reason="No vector PDFs found")
class TestVectorPDFSemanticExtraction:
    """Semantic extraction tests for vector PDFs."""
    
    @patch("app.services.semantic_extractor.genai.Client")
    @pytest.mark.parametrize("pdf_path", VECTOR_PDF_PATHS, ids=VECTOR_PDF_NAMES)
    def test_vector_pdf_image_extraction(self, mock_genai_client, pdf_path, monkeypatch):
        """Test that vector PDFs can be converted to images for semantic extraction."""
        import fitz
        
        monkeypatch.setattr("app.services.semantic_extractor.settings.GOOGLE_API_KEY", "test_key")
        
        # Setup mock
        mock_client = MagicMock()
        mock_genai_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.parsed = SemanticResult()
        mock_client.models.generate_content.return_value = mock_response
        
        # Verify PDF can be opened and converted to image
        doc = fitz.open(pdf_path)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        
        assert pix.width > 0
        assert pix.height > 0
        assert len(pix.tobytes("png")) > 0
        
        doc.close()
        
        # Run extraction
        result = extract_semantics(pdf_path)
        assert isinstance(result, SemanticResult)


@pytest.mark.skipif(not RASTER_PDF_PATHS, reason="No raster PDFs found")
class TestRasterPDFSemanticExtraction:
    """Semantic extraction tests for raster PDFs."""
    
    @patch("app.services.semantic_extractor.genai.Client")
    @pytest.mark.parametrize("pdf_path", RASTER_PDF_PATHS, ids=RASTER_PDF_NAMES)
    def test_raster_pdf_image_extraction(self, mock_genai_client, pdf_path, monkeypatch):
        """Test that raster PDFs can be converted to images for semantic extraction."""
        import fitz
        
        monkeypatch.setattr("app.services.semantic_extractor.settings.GOOGLE_API_KEY", "test_key")
        
        # Setup mock
        mock_client = MagicMock()
        mock_genai_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.parsed = SemanticResult()
        mock_client.models.generate_content.return_value = mock_response
        
        # Verify PDF can be opened and converted to image
        doc = fitz.open(pdf_path)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        
        assert pix.width > 0
        assert pix.height > 0
        assert len(pix.tobytes("png")) > 0
        
        doc.close()
        
        # Run extraction
        result = extract_semantics(pdf_path)
        assert isinstance(result, SemanticResult)
    
    @patch("app.services.semantic_extractor.genai.Client")
    def test_raster_pdfs_suitable_for_vision_api(self, mock_genai_client, monkeypatch):
        """Test that raster PDFs (converted from PNGs) work well with vision API."""
        import fitz
        
        monkeypatch.setattr("app.services.semantic_extractor.settings.GOOGLE_API_KEY", "test_key")
        
        # Setup mock
        mock_client = MagicMock()
        mock_genai_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.parsed = SemanticResult(
            rooms=[RoomLabel(name="Test Room", approximate_center_x=100.0, approximate_center_y=100.0)],
            scale=ScaleInfo(text="1:100", pixels_per_unit=10.0),
            raw_text=[]
        )
        mock_client.models.generate_content.return_value = mock_response
        
        results = []
        
        for pdf_path in RASTER_PDF_PATHS[:5]:  # Test first 5
            doc = fitz.open(pdf_path)
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            
            results.append({
                "name": os.path.basename(pdf_path),
                "width": pix.width,
                "height": pix.height,
                "image_size": len(pix.tobytes("png"))
            })
            
            doc.close()
        
        # All should have valid dimensions
        for r in results:
            assert r["width"] > 0
            assert r["height"] > 0
            assert r["image_size"] > 0
        
        print(f"\nRaster PDF image sizes (sample):")
        for r in results:
            print(f"  {r['name']}: {r['width']}x{r['height']}, {r['image_size']} bytes")


# =============================================================================
# SEMANTIC RESULT MODEL TESTS
# =============================================================================

def test_semantic_result_empty():
    """Test creating an empty SemanticResult."""
    result = SemanticResult()
    
    assert result.rooms == []
    assert result.scale is None
    assert result.raw_text == []


def test_room_label_creation():
    """Test RoomLabel creation."""
    room = RoomLabel(
        name="Living Room",
        approximate_center_x=100.0,
        approximate_center_y=200.0
    )
    
    assert room.name == "Living Room"
    assert room.approximate_center_x == 100.0
    assert room.approximate_center_y == 200.0


def test_scale_info_creation():
    """Test ScaleInfo creation."""
    scale = ScaleInfo(
        text="1/4\" = 1'",
        pixels_per_unit=18.0
    )
    
    assert scale.text == "1/4\" = 1'"
    assert scale.pixels_per_unit == 18.0


def test_semantic_result_multiple_rooms():
    """Test creating a SemanticResult with multiple rooms."""
    result = SemanticResult(
        rooms=[
            RoomLabel(name="Kitchen", approximate_center_x=100.0, approximate_center_y=100.0),
            RoomLabel(name="Bedroom", approximate_center_x=200.0, approximate_center_y=200.0),
            RoomLabel(name="Bathroom", approximate_center_x=300.0, approximate_center_y=100.0),
        ],
        scale=ScaleInfo(text="1/8\" = 1'", pixels_per_unit=9.0),
        raw_text=["Not for construction", "Preliminary design"]
    )
    
    assert len(result.rooms) == 3
    assert result.rooms[0].name == "Kitchen"
    assert result.rooms[1].name == "Bedroom"
    assert result.rooms[2].name == "Bathroom"
    assert len(result.raw_text) == 2
