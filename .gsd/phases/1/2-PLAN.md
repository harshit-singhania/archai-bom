---
phase: 1
plan: 2
wave: 2
---

# Plan 1.2: Layer Filtering & Wall Detection

## Objective

Take the raw vector lines from Plan 1.1 and classify them — separate structural walls from dimension lines, annotations, hatching, and furniture. Output a clean list of wall segments with linear footage. This is the critical signal-to-noise step: a typical CAD PDF has thousands of vector lines, but only ~5–15% are actual walls.

## Context

- .gsd/SPEC.md
- .gsd/RESEARCH.md (Section 1: The Layer Filter)
- app/services/pdf_extractor.py (from Plan 1.1)
- app/models/geometry.py (from Plan 1.1)

## Tasks

<task type="auto">
  <name>Implement wall line classification by thickness and color</name>
  <files>
    app/services/wall_detector.py
    app/models/geometry.py
    tests/test_wall_detector.py
  </files>
  <action>
    1. Add to app/models/geometry.py:
       - WallSegment: x1, y1, x2, y2, length_pts (in PDF points), thickness
       - WallDetectionResult: list of WallSegment, total_wall_count, total_linear_pts

    2. Create app/services/wall_detector.py:
       - detect_walls(extraction: ExtractionResult, wall_thickness_min: float = 1.5) -> WallDetectionResult
       - Heuristic: structural walls in CAD exports are drawn with thicker strokes than dimension lines and annotations
       - Filter lines where width >= wall_thickness_min (configurable threshold)
       - Optionally filter by color (black/dark gray lines are typically structural; light gray/blue are dimensions)
       - Calculate length of each wall segment in PDF points: sqrt((x2-x1)^2 + (y2-y1)^2)
       - Deduplicate near-overlapping segments (within 2pt tolerance) — CAD exports often have double-drawn walls

    3. tests/test_wall_detector.py:
       - Test with known extraction data: mock 10 lines (5 thick, 5 thin) → verify only 5 walls returned
       - Test deduplication: two overlapping thick lines → 1 wall segment
       - Test length calculation accuracy

    Do NOT:
    - Convert to real-world units yet (scale is applied in Plan 1.3)
    - Attempt to detect doors, windows, or rooms (that's spatial graph assembly)
    - Use any ML/AI for classification — pure geometric heuristics for MVP
  </action>
  <verify>
    pytest tests/test_wall_detector.py -v
  </verify>
  <done>
    - detect_walls() filters raw vector lines to wall-only segments by thickness
    - Deduplication removes overlapping segments within tolerance
    - Length calculation is correct (verified by unit test with known coordinates)
    - All tests pass
  </done>
</task>

<task type="auto">
  <name>Integrate extraction + wall detection into a single pipeline call</name>
  <files>
    app/services/ingestion_pipeline.py
    app/api/routes.py
    tests/test_ingestion_pipeline.py
  </files>
  <action>
    1. Create app/services/ingestion_pipeline.py:
       - ingest_pdf(pdf_path: str) -> WallDetectionResult
       - Calls extract_vectors() then detect_walls()
       - Single entry point for downstream consumers

    2. Update app/api/routes.py:
       - POST /api/v1/ingest — accepts PDF file upload (UploadFile)
       - Saves to temp file, runs ingest_pdf(), returns JSON response with wall segments and counts
       - Returns 400 if no vectors found (likely a scanned PDF — not supported)

    3. tests/test_ingestion_pipeline.py:
       - Integration test: real PDF → pipeline → verify wall count > 0

    Do NOT:
    - Add authentication or rate limiting
    - Stream responses — MVP is synchronous
  </action>
  <verify>
    pytest tests/test_ingestion_pipeline.py -v
    curl -X POST http://localhost:5000/api/v1/ingest -F "file=@sample_pdfs/test_floorplan.pdf"
  </verify>
  <done>
    - POST /api/v1/ingest accepts a PDF and returns wall segment JSON
    - Response includes wall_count and wall segments with coordinates
    - Returns 400 for PDFs with no vector data
  </done>
</task>

## Success Criteria

- [ ] Wall detection correctly filters thick structural lines from thin annotation/dimension lines
- [ ] Near-duplicate wall segments are merged
- [ ] Pipeline runs end-to-end: PDF upload → vector extraction → wall detection → JSON response
- [ ] API endpoint functional and tested
