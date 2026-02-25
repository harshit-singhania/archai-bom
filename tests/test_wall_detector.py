"""Tests for wall detector service."""

import pytest

from app.models.geometry import ExtractionResult, VectorLine, WallSegment
from app.services.wall_detector import detect_walls

def test_detect_walls_filters_by_thickness():
    # 5 thick lines (walls), 5 thin lines (dimensions)
    lines = []
    
    # Thick lines
    for i in range(5):
        lines.append(VectorLine(x1=0, y1=i*10, x2=100, y2=i*10, width=2.0))
        
    # Thin lines
    for i in range(5):
        lines.append(VectorLine(x1=0, y1=i*10+5, x2=100, y2=i*10+5, width=0.5))
        
    extraction = ExtractionResult(lines=lines, page_width=800, page_height=600, metadata={})
    
    result = detect_walls(extraction, wall_thickness_min=1.5)
    
    assert result.total_wall_count == 5
    assert len(result.wall_segments) == 5
    assert result.total_linear_pts == 5 * 100.0

def test_detect_walls_deduplicates():
    # Two thick lines perfectly overlapping
    lines = [
        VectorLine(x1=10, y1=10, x2=50, y2=10, width=2.0),
        VectorLine(x1=10, y1=10, x2=50, y2=10, width=2.0),
    ]
    
    extraction = ExtractionResult(lines=lines, page_width=800, page_height=600, metadata={})
    result = detect_walls(extraction)
    
    assert result.total_wall_count == 1
    assert result.total_linear_pts == 40.0

def test_detect_walls_deduplicates_within_tolerance():
    # Two thick lines close but not identical
    lines = [
        VectorLine(x1=10, y1=10, x2=50, y2=10, width=2.0),
        # Shifted by 1 pt in X and Y (within 2pt tolerance for start and end)
        VectorLine(x1=11, y1=11, x2=51, y2=11, width=2.0),
    ]
    
    extraction = ExtractionResult(lines=lines, page_width=800, page_height=600, metadata={})
    result = detect_walls(extraction)
    
    assert result.total_wall_count == 1

def test_detect_walls_length_calculation():
    # 3-4-5 triangle line
    lines = [
        VectorLine(x1=0, y1=0, x2=30, y2=40, width=2.0)
    ]
    
    extraction = ExtractionResult(lines=lines, page_width=800, page_height=600, metadata={})
    result = detect_walls(extraction)
    
    assert result.total_wall_count == 1
    assert result.wall_segments[0].length_pts == 50.0
