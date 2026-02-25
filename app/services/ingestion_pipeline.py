"""Ingestion pipeline service."""

from app.models.geometry import WallDetectionResult
from app.services.pdf_extractor import extract_vectors
from app.services.wall_detector import detect_walls

def ingest_pdf(pdf_path: str) -> WallDetectionResult:
    """
    Ingest a PDF floorplan and return detected walls.
    
    Extracts vectors from the PDF, then filters and detects 
    structural walls. Raises ValueError if no vectors are found
    (scanned image instead of CAD export).
    """
    extraction = extract_vectors(pdf_path)
    
    if not extraction.lines:
        raise ValueError("No vector data found in PDF. This might be a scanned image.")
        
    result = detect_walls(extraction)
    return result
