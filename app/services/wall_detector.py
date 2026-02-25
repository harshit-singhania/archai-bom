"""Wall detection service."""

import math
from typing import List

from app.models.geometry import ExtractionResult, WallDetectionResult, WallSegment, VectorLine

def detect_walls(extraction: ExtractionResult, wall_thickness_min: float = 1.5) -> WallDetectionResult:
    """
    Detect structural walls from raw vector lines using heuristics.
    
    Heuristic: structural walls in CAD exports are drawn with thicker strokes
    than dimension lines and annotations.
    """
    # Filter by thickness first
    thick_lines = [line for line in extraction.lines if line.width >= wall_thickness_min]
    
    # Optional color filtering: in CAD, structural walls are often black/dark gray.
    # Currently relying primarily on thickness to be robust across different CAD exports.
    
    # Convert VectorLines to WallSegments
    raw_segments: List[WallSegment] = []
    for line in thick_lines:
        # Standardize direction so checking overlaps is easier
        # E.g., always go left-to-right, or top-to-bottom
        x1, y1 = line.x1, line.y1
        x2, y2 = line.x2, line.y2
        
        if x1 > x2 or (x1 == x2 and y1 > y2):
            x1, y1, x2, y2 = x2, y2, x1, y1
            
        length = line.length()
        if length > 0.1:  # ignore tiny dots
            raw_segments.append(WallSegment(
                x1=x1, y1=y1, x2=x2, y2=y2,
                length_pts=length,
                thickness=line.width
            ))
            
    # Deduplicate near-overlapping segments (within 2pt tolerance)
    deduped_segments: List[WallSegment] = []
    tolerance = 2.0
    
    for seg in raw_segments:
        is_dup = False
        for existing in deduped_segments:
            # Check if start and end points are close
            start_dist = math.hypot(seg.x1 - existing.x1, seg.y1 - existing.y1)
            end_dist = math.hypot(seg.x2 - existing.x2, seg.y2 - existing.y2)
            
            if start_dist <= tolerance and end_dist <= tolerance:
                is_dup = True
                break
                
        if not is_dup:
            deduped_segments.append(seg)
            
    total_count = len(deduped_segments)
    total_linear = sum(seg.length_pts for seg in deduped_segments)
    
    return WallDetectionResult(
        wall_segments=deduped_segments,
        total_wall_count=total_count,
        total_linear_pts=total_linear
    )
