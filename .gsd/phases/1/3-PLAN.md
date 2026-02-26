---
phase: 1
plan: 3
wave: 3
---

# Plan 1.3: Semantic Extraction & Spatial Graph Assembly

## Objective

Complete the ingestion pipeline by adding semantic understanding (room names, scale) via Google Gemini and assembling wall segments into a structured spatial graph with labeled rooms and real-world dimensions. This is the final deliverable of Phase 1: a clean JSON spatial graph that Phase 2 (Spatial Generation) and Phase 3 (Deterministic Calculator) consume.

## Context

- .gsd/SPEC.md
- .gsd/RESEARCH.md (Section 1: The Semantic Brain + The Merge)
- app/services/pdf_extractor.py (Plan 1.1)
- app/services/wall_detector.py (Plan 1.2)
- app/services/ingestion_pipeline.py (Plan 1.2)

## Tasks

<task type="auto">
  <name>Implement Google Gemini semantic extraction from PDF raster</name>
  <files>
    app/services/semantic_extractor.py
    app/models/semantic.py
    app/core/config.py
    tests/test_semantic_extractor.py
    .env.example
  </files>
  <action>
    1. app/models/semantic.py — Define Pydantic models:
       - RoomLabel: name (str), approximate_center_x (float), approximate_center_y (float)
       - ScaleInfo: text (str, e.g. "1/4\" = 1'"), pixels_per_unit (float, calculated)
       - SemanticResult: rooms (list[RoomLabel]), scale (ScaleInfo | None), raw_text (list[str])

    2. app/core/config.py — Add GOOGLE_API_KEY to settings

    3. .env.example — Document required env vars (GOOGLE_API_KEY)

    4. app/services/semantic_extractor.py:
       - extract_semantics(pdf_path: str, page_num: int = 0) -> SemanticResult
       - Convert PDF page to raster image using fitz (page.get_pixmap())
       - Send image to Google Gemini vision with structured prompt:
         "Extract from this architectural floorplan: 1) All room names/labels with approximate positions, 2) The drawing scale if stated, 3) Any dimension text visible"
       - Parse response into SemanticResult (use Gemini's JSON response format)
       - Handle API errors gracefully — return empty SemanticResult on failure (vector data alone is still useful)

    Do NOT:
    - Use Gemini for ANY geometric measurement — measurements come from PyMuPDF vectors only
    - Cache or batch API calls (premature optimization)
    - Fall back to OCR libraries — Gemini handles text extraction from architectural drawings better than Tesseract
  </action>
  <verify>
    pytest tests/test_semantic_extractor.py -v
  </verify>
  <done>
    - extract_semantics() sends PDF raster to Google Gemini and returns room labels
    - Room names are extracted with approximate positions
    - Scale text is extracted if present
    - Graceful degradation: returns empty result on API failure, does not crash pipeline
  </done>
</task>

<task type="auto">
  <name>Build spatial graph by merging vectors + semantics</name>
  <files>
    app/services/spatial_graph.py
    app/models/spatial.py
    app/services/ingestion_pipeline.py
    tests/test_spatial_graph.py
  </files>
  <action>
    1. app/models/spatial.py — Define the spatial graph model:
       - Room: name (str), boundary_walls (list of wall segment indices), area_sq_pts (float), area_sq_ft (float | None)
       - SpatialGraph: walls (list[WallSegment]), rooms (list[Room]), scale_factor (float | None), page_dimensions (tuple)
       - Method: to_json() → serializable dict for downstream consumption

    2. app/services/spatial_graph.py:
       - build_spatial_graph(walls: WallDetectionResult, semantics: SemanticResult) -> SpatialGraph
       - Step 1: Take wall segments and attempt to form closed polygons (rooms) using endpoint proximity matching (tolerance: 5 PDF points)
       - Step 2: For each closed polygon, calculate area using the shoelace formula
       - Step 3: Match room labels from semantics to polygons by checking if label center point falls inside polygon (point-in-polygon test)
       - Step 4: If scale is available, convert PDF-point areas to real-world square footage
       - Step 5: Label unmatched rooms as "Unknown Room N"

    3. Update app/services/ingestion_pipeline.py:
       - ingest_pdf() now calls extract_vectors → detect_walls → extract_semantics → build_spatial_graph
       - Returns SpatialGraph instead of WallDetectionResult
       - Works without Google API key: if semantic extraction fails, builds graph with "Unknown Room" labels

    4. tests/test_spatial_graph.py:
       - Test with a simple rectangle (4 walls) → 1 room detected, area calculated correctly
       - Test with two adjacent rectangles → 2 rooms detected
       - Test label assignment: center point inside polygon → room named correctly

    Do NOT:
    - Handle complex curved walls (MVP assumes straight segments only)
    - Implement room-type inference (that's Phase 2)
    - Persist the graph to a database (in-memory for MVP)
  </action>
  <verify>
    pytest tests/test_spatial_graph.py -v
  </verify>
  <done>
    - Closed wall polygons are detected and form rooms
    - Room areas are calculated via shoelace formula
    - Semantic labels are matched to rooms by point-in-polygon
    - Scale conversion works when scale info is available
    - Full pipeline: PDF → SpatialGraph JSON with labeled rooms and areas
  </done>
</task>

<task type="checkpoint:human-verify">
  <name>End-to-end validation with real floorplan</name>
  <files>
    sample_pdfs/
    app/services/ingestion_pipeline.py
  </files>
  <action>
    Run full pipeline on a real CAD-exported floorplan PDF:
    1. Upload via POST /api/v1/ingest
    2. Inspect returned SpatialGraph JSON
    3. User verifies: room count is correct, room names match, areas are plausible

    Print formatted summary:
    - Total walls detected
    - Rooms found (name, area in sq ft)
    - Scale factor used
    - Any unmatched/unknown rooms
  </action>
  <verify>
    curl -X POST http://localhost:5000/api/v1/ingest -F "file=@sample_pdfs/test_floorplan.pdf" | python -m json.tool
  </verify>
  <done>
    User confirms:
    - Room count matches the floorplan
    - Room names are correctly assigned
    - Square footage is within ~10% of manual measurement
    - Phase 1 objective is met: PDF → structured spatial graph
  </done>
</task>

## Success Criteria

- [ ] Google Gemini extracts room names and scale from PDF raster image
- [ ] Wall segments form closed polygons that represent rooms
- [ ] Room areas calculated correctly via shoelace formula
- [ ] Semantic labels matched to rooms by point-in-polygon
- [ ] Full pipeline: PDF upload → SpatialGraph JSON with labeled rooms, areas, and wall segments
- [ ] Pipeline degrades gracefully without Google API key (vector-only mode)
