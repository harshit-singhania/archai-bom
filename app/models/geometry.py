"""Pydantic models for geometric data."""

from typing import List, Tuple, Optional
from pydantic import BaseModel, Field


class VectorLine(BaseModel):
    """A single vector line segment extracted from a PDF.
    
    Coordinates are in PDF points (1/72 inch).
    """
    x1: float = Field(..., description="Start X coordinate")
    y1: float = Field(..., description="Start Y coordinate")
    x2: float = Field(..., description="End X coordinate")
    y2: float = Field(..., description="End Y coordinate")
    width: float = Field(default=0.0, description="Line stroke width in points")
    color: Optional[Tuple[float, float, float]] = Field(
        default=None, description="RGB color tuple (0-1 range)"
    )
    
    def length(self) -> float:
        """Calculate the Euclidean length of the line."""
        return ((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2) ** 0.5
    
    def is_horizontal(self, tolerance: float = 0.1) -> bool:
        """Check if line is approximately horizontal."""
        return abs(self.y2 - self.y1) < tolerance
    
    def is_vertical(self, tolerance: float = 0.1) -> bool:
        """Check if line is approximately vertical."""
        return abs(self.x2 - self.x1) < tolerance


class ExtractionResult(BaseModel):
    """Result of vector extraction from a PDF page."""
    lines: List[VectorLine] = Field(default_factory=list, description="Extracted vector lines")
    page_width: float = Field(..., description="Page width in points")
    page_height: float = Field(..., description="Page height in points")
    metadata: dict = Field(default_factory=dict, description="Additional PDF metadata")
    
    def get_line_count(self) -> int:
        """Return total number of lines."""
        return len(self.lines)
    
    def get_unique_widths(self) -> List[float]:
        """Return sorted list of unique line widths."""
        widths = sorted(set(round(line.width, 2) for line in self.lines))
        return widths
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Return bounding box of all lines (min_x, min_y, max_x, max_y)."""
        if not self.lines:
            return (0, 0, 0, 0)
        
        min_x = min(min(line.x1, line.x2) for line in self.lines)
        min_y = min(min(line.y1, line.y2) for line in self.lines)
        max_x = max(max(line.x1, line.x2) for line in self.lines)
        max_y = max(max(line.y1, line.y2) for line in self.lines)
        
        return (min_x, min_y, max_x, max_y)


class WallSegment(BaseModel):
    """A detected wall segment with length and thickness."""
    x1: float = Field(..., description="Start X coordinate")
    y1: float = Field(..., description="Start Y coordinate")
    x2: float = Field(..., description="End X coordinate")
    y2: float = Field(..., description="End Y coordinate")
    length_pts: float = Field(..., description="Length in PDF points")
    thickness: float = Field(..., description="Wall thickness in points")


class WallDetectionResult(BaseModel):
    """Result of wall detection from extracted vectors or raster vision."""
    wall_segments: List[WallSegment] = Field(default_factory=list, description="List of detected wall segments")
    total_wall_count: int = Field(default=0, description="Total number of walls detected")
    total_linear_pts: float = Field(default=0.0, description="Total linear points of all walls")
    source: str = Field(default="vector", description="Extraction source: 'vector' or 'raster'")
