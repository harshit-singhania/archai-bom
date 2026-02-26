"""Ingestion pipeline service."""

import logging

from app.models.geometry import WallDetectionResult
from app.services.pdf_extractor import extract_vectors
from app.services.wall_detector import detect_walls
from app.services.raster_wall_extractor import extract_walls_from_raster

logger = logging.getLogger(__name__)


def ingest_pdf(pdf_path: str) -> WallDetectionResult:
    """
    Ingest a PDF floorplan and return detected walls.

    Attempts vector extraction first (fast, free, precise). If no vector
    graphics are found (scanned/raster PDF), falls back to Gemini vision-based
    wall extraction.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        WallDetectionResult with source='vector' or source='raster'

    Raises:
        RuntimeError: If raster fallback is required but GOOGLE_API_KEY is not set
        ValueError: If the PDF cannot be processed by either path
    """
    extraction = extract_vectors(pdf_path)

    if extraction.lines:
        result = detect_walls(extraction)
        return result

    # No vector graphics found — try raster vision fallback
    logger.info(
        "No vector data found in %s. Attempting raster wall extraction via Gemini.",
        pdf_path,
    )
    return extract_walls_from_raster(pdf_path)
