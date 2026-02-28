"""Raster wall extraction service using Google Gemini vision."""

import logging
import math
from typing import List

import fitz  # PyMuPDF
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.geometry import WallDetectionResult, WallSegment

logger = logging.getLogger(__name__)

# Scale factor used when rasterizing PDF pages (pixels per PDF point)
_RASTER_SCALE = 2.0


class _WallSegmentPx(BaseModel):
    """A wall segment in pixel coordinates, as returned by Gemini."""

    x1: float = Field(..., description="Start X in pixels")
    y1: float = Field(..., description="Start Y in pixels")
    x2: float = Field(..., description="End X in pixels")
    y2: float = Field(..., description="End Y in pixels")
    thickness_px: float = Field(default=5.0, description="Estimated wall thickness in pixels")


class _RasterWallResult(BaseModel):
    """Gemini structured output schema for raster wall detection."""

    walls: List[_WallSegmentPx] = Field(
        default_factory=list,
        description="List of detected wall line segments",
    )


def extract_walls_from_raster(pdf_path: str, page_num: int = 0) -> WallDetectionResult:
    """
    Extract wall segments from a raster (scanned) PDF page using Gemini vision.

    Rasterizes the PDF page to a PNG image, sends it to Gemini, and parses
    the structured response into a WallDetectionResult matching the vector
    pipeline output format.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to extract from (0-indexed, default: 0)

    Returns:
        WallDetectionResult containing detected wall segments

    Raises:
        RuntimeError: If GOOGLE_API_KEY is not set
        ValueError: If the PDF page cannot be rasterized
    """
    if not settings.GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Raster PDF processing requires Gemini vision."
        )

    # Rasterize the PDF page
    try:
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            raise ValueError(f"Page {page_num} not found. PDF has {len(doc)} pages.")

        page = doc[page_num]
        page_width = page.rect.width
        page_height = page.rect.height
        pix = page.get_pixmap(matrix=fitz.Matrix(_RASTER_SCALE, _RASTER_SCALE))
        img_bytes = pix.tobytes("png")
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise ValueError(f"Failed to rasterize PDF page: {exc}") from exc
    finally:
        if "doc" in locals():
            doc.close()

    # Call Gemini Vision
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                (
                    "You are an expert architectural analyst specializing in floor plan interpretation.\n"
                    "Analyze the provided floor plan image and identify ALL structural wall line segments.\n\n"
                    "Focus on:\n"
                    "- Thick, continuous lines forming the building perimeter\n"
                    "- Thick lines dividing interior rooms\n"
                    "- Double-line walls (treat each pair as a single segment along the wall centerline)\n\n"
                    "Ignore:\n"
                    "- Thin dimension lines, arrows, and annotation text\n"
                    "- Door swings, window symbols, and furniture\n"
                    "- Hatch patterns and fill areas\n\n"
                    f"The image was rendered at {_RASTER_SCALE}x scale from a PDF. "
                    f"Return wall coordinates as pixel positions in the image.\n"
                    "For each wall, return:\n"
                    "  - x1, y1: start point in pixels\n"
                    "  - x2, y2: end point in pixels\n"
                    "  - thickness_px: estimated wall thickness in pixels (e.g., 8-20 for structural walls)\n\n"
                    "Return a complete list covering all wall segments."
                ),
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_RasterWallResult,
                temperature=0.1,
            ),
        )

        raster_result: _RasterWallResult = response.parsed
        if raster_result is None:
            logger.warning("Gemini returned no parsed result for raster wall extraction.")
            raster_result = _RasterWallResult()

    except Exception as exc:
        raise RuntimeError(f"Gemini vision call failed for raster wall extraction: {exc}") from exc

    # Convert pixel coordinates to PDF points and build WallDetectionResult
    wall_segments = _convert_to_wall_segments(raster_result.walls, _RASTER_SCALE)

    total_linear = sum(seg.length_pts for seg in wall_segments)
    return WallDetectionResult(
        wall_segments=wall_segments,
        total_wall_count=len(wall_segments),
        total_linear_pts=total_linear,
        source="raster",
    )


def _convert_to_wall_segments(
    px_walls: List[_WallSegmentPx], scale: float
) -> List[WallSegment]:
    """Convert pixel-coordinate walls to PDF-point WallSegments."""
    segments: List[WallSegment] = []

    for wall in px_walls:
        # Convert pixels → PDF points
        x1 = wall.x1 / scale
        y1 = wall.y1 / scale
        x2 = wall.x2 / scale
        y2 = wall.y2 / scale
        thickness = wall.thickness_px / scale

        # Standardize direction (left-to-right / top-to-bottom) — matches vector pipeline
        if x1 > x2 or (x1 == x2 and y1 > y2):
            x1, y1, x2, y2 = x2, y2, x1, y1

        length = math.hypot(x2 - x1, y2 - y1)
        if length < 0.1:
            continue  # skip degenerate segments

        segments.append(
            WallSegment(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                length_pts=length,
                thickness=thickness,
            )
        )

    return segments
