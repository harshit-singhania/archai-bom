"""PDF vector extraction service using PyMuPDF."""

from typing import List, Optional, Tuple
import fitz  # PyMuPDF

from app.models.geometry import VectorLine, ExtractionResult


def extract_vectors(pdf_path: str, page_num: int = 0) -> ExtractionResult:
    """
    Extract vector lines from a CAD-exported PDF using PyMuPDF.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to extract from (0-indexed, default: 0)
    
    Returns:
        ExtractionResult containing all vector lines and metadata
    
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If page_num is invalid
    """
    doc = fitz.open(pdf_path)
    
    try:
        if page_num >= len(doc):
            raise ValueError(f"Page {page_num} not found. PDF has {len(doc)} pages.")
        
        page = doc[page_num]
        page_rect = page.rect
        
        lines: List[VectorLine] = []
        
        # Get all drawings/vector graphics on the page
        drawings = page.get_drawings()
        
        for drawing in drawings:
            # Extract line width and color from drawing properties
            stroke_width = drawing.get("width", 0.0)
            stroke_color = _parse_color(drawing.get("color"))
            
            # Process each item in the drawing
            for item in drawing.get("items", []):
                item_type = item[0]
                
                if item_type == "l":  # Line segment
                    # item is ("l", start_point, end_point)
                    start_pt = item[1]
                    end_pt = item[2]
                    
                    line = VectorLine(
                        x1=float(start_pt.x),
                        y1=float(start_pt.y),
                        x2=float(end_pt.x),
                        y2=float(end_pt.y),
                        width=float(stroke_width),
                        color=stroke_color,
                    )
                    lines.append(line)
                    
                elif item_type == "re":  # Rectangle
                    # item is ("re", rect)
                    rect = item[1]
                    # Convert rectangle to 4 line segments
                    rect_lines = _rect_to_lines(rect, stroke_width, stroke_color)
                    lines.extend(rect_lines)
                    
        # Extract metadata
        metadata = {
            "page_number": page_num + 1,
            "total_pages": len(doc),
            "pdf_version": doc.metadata.get("format", "unknown"),
        }
        
        return ExtractionResult(
            lines=lines,
            page_width=float(page_rect.width),
            page_height=float(page_rect.height),
            metadata=metadata,
        )
        
    finally:
        doc.close()


def _parse_color(color_value) -> Optional[Tuple[float, float, float]]:
    """Parse color value from PyMuPDF to RGB tuple."""
    if color_value is None:
        return None
    
    # Handle different color formats from PyMuPDF
    if isinstance(color_value, (list, tuple)) and len(color_value) >= 3:
        return (float(color_value[0]), float(color_value[1]), float(color_value[2]))
    
    return None


def _rect_to_lines(rect, width: float, color) -> List[VectorLine]:
    """Convert a rectangle to 4 line segments."""
    lines = []
    
    # Rectangle corners: top-left, top-right, bottom-right, bottom-left
    corners = [
        (float(rect.x0), float(rect.y0)),  # top-left
        (float(rect.x1), float(rect.y0)),  # top-right
        (float(rect.x1), float(rect.y1)),  # bottom-right
        (float(rect.x0), float(rect.y1)),  # bottom-left
    ]
    
    # Create 4 lines: top, right, bottom, left
    for i in range(4):
        start = corners[i]
        end = corners[(i + 1) % 4]
        
        line = VectorLine(
            x1=start[0],
            y1=start[1],
            x2=end[0],
            y2=end[1],
            width=float(width),
            color=color,
        )
        lines.append(line)
    
    return lines


def extract_summary(pdf_path: str, page_num: int = 0) -> dict:
    """
    Get a quick summary of vector extraction from a PDF.
    
    Useful for debugging and verification.
    """
    result = extract_vectors(pdf_path, page_num)
    
    bbox = result.get_bounding_box()
    widths = result.get_unique_widths()
    
    return {
        "total_lines": len(result.lines),
        "page_dimensions": (result.page_width, result.page_height),
        "bounding_box": bbox,
        "unique_line_widths": widths,
        "width_count": len(widths),
    }
