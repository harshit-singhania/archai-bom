"""Pydantic models for semantic data."""

from typing import List, Optional
from pydantic import BaseModel, Field


class RoomLabel(BaseModel):
    """A recognized room label with approximate center coordinates."""
    name: str = Field(..., description="Name of the room (e.g., 'Master Bedroom', 'Kitchen')")
    approximate_center_x: float = Field(..., description="Approximate X coordinate of label center in PDF points")
    approximate_center_y: float = Field(..., description="Approximate Y coordinate of label center in PDF points")


class ScaleInfo(BaseModel):
    """Information about the drawing scale if present."""
    text: str = Field(..., description="Raw text of the scale, e.g., '1/4\" = 1''")
    pixels_per_unit: float = Field(..., description="Calculated PDF points per real-world unit (typically 1 foot)")


class SemanticResult(BaseModel):
    """Result of semantic extraction via GPT-4o-mini."""
    rooms: List[RoomLabel] = Field(default_factory=list, description="List of recognized rooms")
    scale: Optional[ScaleInfo] = Field(default=None, description="Scale information if detected")
    raw_text: List[str] = Field(default_factory=list, description="Other text detected on the page")
