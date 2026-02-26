---
phase: 2
plan: 1
wave: 1
---

# Plan 2.1: Layout DSL Schema & Gemini Generation Service

## Objective

Define the JSON DSL schema that represents a generated interior layout, and build the core Gemini-based generation service that converts a SpatialGraph + natural language prompt into a structured layout. This is the foundational building block of Phase 2 — downstream plans (constraint checking, iteration loop) consume the GeneratedLayout model and the raw generation service.

## Context

- .gsd/SPEC.md
- .gsd/RESEARCH.md (Section 2: Spatial Generation Model)
- app/models/spatial.py (SpatialGraph — Phase 1 output, Phase 2 input contract)
- app/models/geometry.py (WallSegment model)
- app/services/semantic_extractor.py (reference for Gemini API usage patterns)
- app/core/config.py (GOOGLE_API_KEY already configured)

## Tasks

<task type="auto">
  <name>Define Layout JSON DSL as Pydantic models</name>
  <files>
    app/models/layout.py
    tests/test_layout_models.py
  </files>
  <action>
    1. Create app/models/layout.py with these Pydantic models:

       - InteriorWall:
         - id: str (e.g. "iw_1")
         - x1, y1, x2, y2: float (coordinates in millimeters, real-world scale)
         - thickness_mm: float (default 100mm for standard drywall partition)
         - material: str (default "drywall" — matches materials_pricing table)

       - Door:
         - id: str (e.g. "d_1")
         - wall_id: str (references InteriorWall.id or a perimeter wall)
         - position_along_wall: float (0.0 to 1.0 — fraction of wall length)
         - width_mm: float (standard: 900mm single, 1200mm double)
         - swing_direction: Literal["left", "right", "sliding"]
         - door_type: Literal["single", "double", "sliding"]

       - Fixture:
         - id: str (e.g. "f_1")
         - room_name: str (which room this belongs to)
         - fixture_type: str (e.g. "desk", "dental_chair", "conference_table", "reception_counter")
         - center_x, center_y: float (mm)
         - width_mm, depth_mm: float
         - rotation_deg: float (0-360)

       - GeneratedRoom:
         - name: str (e.g. "Operatory 1")
         - room_type: str (e.g. "operatory", "reception", "corridor", "restroom")
         - boundary: list[tuple[float, float]] (polygon vertices in mm, closed)
         - area_sqm: float

       - GeneratedLayout:
         - rooms: list[GeneratedRoom]
         - interior_walls: list[InteriorWall]
         - doors: list[Door]
         - fixtures: list[Fixture]
         - grid_size_mm: int (default 50)
         - prompt: str (original NL prompt)
         - perimeter_walls: list[dict] (copied from SpatialGraph for reference)
         - page_dimensions_mm: tuple[float, float] (real-world perimeter size)

       - Add a to_json() method on GeneratedLayout that returns a serializable dict
       - Add model_config with json_schema_extra examples for Gemini structured output

    2. tests/test_layout_models.py:
       - Test valid GeneratedLayout construction with all fields
       - Test validation rejects negative dimensions
       - Test to_json() round-trips correctly (serialize → deserialize → equal)
       - Test Door.position_along_wall must be 0.0-1.0

    Do NOT:
    - Add database persistence models — that's Phase 4
    - Add rendering/SVG logic — that's Phase 4
    - Over-constrain fixture_type to a fixed enum — keep it as str for flexibility; room-type templates will come later
  </action>
  <verify>
    pytest tests/test_layout_models.py -v
  </verify>
  <done>
    - All Pydantic models defined with proper validation
    - to_json() serialization works
    - Unit tests pass for valid and invalid payloads
    - Models are importable as: from app.models.layout import GeneratedLayout
  </done>
</task>

<task type="auto">
  <name>Build Gemini layout generation service</name>
  <files>
    app/services/layout_generator.py
    tests/test_layout_generator.py
  </files>
  <action>
    1. Create app/services/layout_generator.py:

       - generate_layout(spatial_graph: SpatialGraph, prompt: str) -> GeneratedLayout

       - Step 1: Convert SpatialGraph from PDF points to real-world millimeters using scale_factor
         - If scale_factor is None, assume 1 PDF point = 1mm (best guess fallback)
         - Calculate perimeter bounding box in mm

       - Step 2: Build the Gemini prompt. The prompt must include:
         - The perimeter wall coordinates in mm (from SpatialGraph.walls converted to mm)
         - Room names and areas from SpatialGraph.rooms (if any exist from Phase 1 semantic extraction)
         - The user's natural language description (e.g. "6 operatory dental clinic with reception, waiting area, sterilization room")
         - Explicit instruction: "Generate interior walls, doors, and fixtures that subdivide the perimeter into the described rooms. All coordinates must be in millimeters." (Do NOT instruct Gemini to snap to grid — grid snapping is handled post-generation in Plan 2.2)
         - The JSON schema of GeneratedLayout (use model_json_schema())

       - Step 3: Call Google Gemini (model: gemini-2.5-flash) with:
         - The constructed prompt as text (no image needed — this is generation, not extraction)
         - response_mime_type="application/json"
         - response_schema=GeneratedLayout schema
         - Follow the same client pattern as semantic_extractor.py

       - Step 4: Parse Gemini JSON response into GeneratedLayout Pydantic model
         - If parsing fails, raise a descriptive ValueError with the raw response

       - Handle API errors: raise RuntimeError with context (don't silently degrade — generation is the core function, not optional like semantic extraction)

    2. tests/test_layout_generator.py:
       - Mock the Gemini API call (same pattern as test_semantic_extractor.py)
       - Test with a simple rectangular SpatialGraph (one room, 10m x 8m perimeter)
       - Test that the prompt includes perimeter coordinates and user description
       - Test that response is parsed into valid GeneratedLayout
       - Test error handling: malformed Gemini response raises ValueError

    Do NOT:
    - Add constraint checking here — that's Plan 2.2
    - Add retry/iteration logic — that's Plan 2.3
    - Send images to Gemini — layout generation is text-to-JSON, not vision
    - Use LangGraph yet — the simple generation service is just a function call; the loop comes in Plan 2.3
  </action>
  <verify>
    pytest tests/test_layout_generator.py -v
  </verify>
  <done>
    - generate_layout() converts SpatialGraph to mm, sends prompt to Gemini, returns GeneratedLayout
    - Prompt includes perimeter coordinates, room context, and user description
    - Gemini structured output is parsed into validated Pydantic model
    - Tests pass with mocked API calls
  </done>
</task>

## Success Criteria

- [ ] Layout DSL schema defined as Pydantic models in app/models/layout.py
- [ ] GeneratedLayout model validates interior walls, doors, fixtures, and room boundaries
- [ ] generate_layout() sends SpatialGraph + prompt to Gemini and returns structured layout
- [ ] Coordinate conversion from PDF points to real-world mm works correctly
- [ ] All tests pass with mocked Gemini API
