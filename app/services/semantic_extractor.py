"""Semantic extraction service using Google Gemini vision."""

import base64
import json
import logging
from typing import Optional

import fitz  # PyMuPDF
from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import settings
from app.models.semantic import SemanticResult

logger = logging.getLogger(__name__)


def extract_semantics(pdf_path: str, page_num: int = 0) -> SemanticResult:
    """
    Extract semantic information (rooms, scale) from a PDF page using Google Gemini.

    Converts the PDF page to a raster image, sends it to the vision model,
    and parses the structured JSON response into a SemanticResult.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to extract from (0-indexed, default: 0)

    Returns:
        SemanticResult containing room labels and scale information
    """
    if not settings.GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set. Skipping semantic extraction.")
        return SemanticResult()

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    # 1. Convert PDF page to raster image
    try:
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            logger.error(f"Page {page_num} not found in {pdf_path}")
            return SemanticResult()

        page = doc[page_num]
        logger.debug(
            f"Extraction Page dimensions: width={page.rect.width}, height={page.rect.height}"
        )
        # Use a moderate DPI (e.g., 150) to balance detail and API token limits
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img_bytes = pix.tobytes("png")
        base64_image = base64.b64encode(img_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to rasterize PDF for semantic extraction: {e}")
        return SemanticResult()
    finally:
        if "doc" in locals():
            doc.close()

    # 2. Call Gemini Vision with Structured Output
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                (
                    "You are an expert architectural draftsperson. Extract semantic information "
                    "from the provided architectural floorplan. We need three things:\n"
                    "1. Room labels: Identifying text like 'Master Bedroom', 'Bath', 'Kitchen'. "
                    "Estimate their approximate (X, Y) center coordinates relative to the top-left of the image "
                    "(0,0). Note that the original PDF is likely 72 DPI. Please scale your pixel estimates back "
                    "if needed, though approximate coordinates are fine.\n"
                    "2. Drawing scale: Look for text like 'Scale: 1/4\" = 1'' or '1:100'. Extract the raw text "
                    "and calculate the 'pixels_per_unit' multiplier (e.g. if 1/4 inch equals 1 foot, and 1 inch is "
                    "72 points, then 1/4 inch is 18 points. Thus pixels_per_unit = 18.0).\n"
                    "3. Raw text: Any other notable text on the page."
                ),
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SemanticResult,
                temperature=0.1,
            ),
        )

        result = response.parsed
        return result if result else SemanticResult()

    except ValidationError as e:
        logger.error(f"Failed to parse Gemini response into SemanticResult: {e}")
        return SemanticResult()
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return SemanticResult()
