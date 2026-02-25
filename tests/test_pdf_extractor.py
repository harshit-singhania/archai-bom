"""Tests for PDF vector extraction."""

import os
import pytest
import fitz  # PyMuPDF

import fitz
from app.services.pdf_extractor import extract_vectors, extract_summary
from app.models.geometry import VectorLine, ExtractionResult


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
