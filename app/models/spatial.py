"""Pydantic models for the assembled spatial graph."""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

from app.models.geometry import WallSegment


class Room(BaseModel):
    """A detected room characterized by bounding walls and optional semantic label."""
    name: str = Field(..., description="Name of the room, either from semantics or 'Unknown Room N'")
    boundary_walls: List[int] = Field(..., description="Indices of WallSegments that make up this room")
    area_sq_pts: float = Field(..., description="Calculated area in PDF square points")
    area_sq_ft: Optional[float] = Field(default=None, description="Calculated area in square feet if scale is known")


class SpatialGraph(BaseModel):
    """The complete structured representation of a floorplan."""
    walls: List[WallSegment] = Field(default_factory=list, description="All structural wall segments")
    rooms: List[Room] = Field(default_factory=list, description="All detected rooms")
    scale_factor: Optional[float] = Field(default=None, description="Pixels per foot scale if detected")
    page_dimensions: Tuple[float, float] = Field(..., description="(width, height) of the PDF page in points")
    
    def to_json(self) -> dict:
        """Return generic serializable dictionary."""
        return self.model_dump()
