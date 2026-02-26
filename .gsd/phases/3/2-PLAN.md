---
phase: 3
plan: 2
wave: 1
---

# Plan 3.2: Geometry-to-Quantity Rules Engine

## Objective
Implement the deterministic calculators that convert `GeneratedLayout` geometry into material quantities. No AI in this layer — pure math from geometry dimensions to sqft/rft/pieces. Each calculator handles one BOM category.

## Context
- `.gsd/SPEC.md` — "No hallucination in BOM", "deterministic calculator"
- `.gsd/phases/3/RESEARCH.md` — Q2 (categories + calculation rules), Q5 (ceiling height)
- `app/models/layout.py` — `GeneratedLayout`, `InteriorWall`, `GeneratedRoom`, `Door`, `Fixture`
- `app/models/bom.py` — `BOMLineItem` (created in Plan 3.1)
- `app/data/material_catalog.py` — `get_material_for_room()` (created in Plan 3.1)

## Tasks

<task type="auto">
  <name>Implement wall and door quantity calculators</name>
  <files>app/services/bom_calculators.py</files>
  <action>
    Create a module with pure functions that take geometry and return `List[BOMLineItem]`.

    1. `calculate_wall_quantities(walls: List[InteriorWall], ceiling_height_mm: float) -> List[BOMLineItem]`:
       - For each interior wall:
         - Wall area = length × ceiling_height (both sides) → convert mm² to sqft (÷ 92903.04)
         - Emit 2 line items per wall: "Gypsum Board 12.5mm" + "Metal Stud Frame (GI)"
         - If wall.material == "glass", emit "Glass Partition 12mm" instead (1 side only)
       - Length = hypot(x2-x1, y2-y1) in mm

    2. `calculate_door_quantities(doors: List[Door]) -> List[BOMLineItem]`:
       - Count doors by type
       - Map door_type to material: "single"/"double" → "Flush Door", "sliding" → "Glass Door"
       - Emit 1 line item per door

    Important:
    - All functions are PURE — no side effects, no API calls, no database access
    - Use `math.hypot` for wall lengths
    - Conversion factor: 1 sqft = 92903.04 mm²
    - Conversion factor: 1 rft = 304.8 mm
  </action>
  <verify>pytest tests/test_bom_calculators.py -k "wall or door" -v</verify>
  <done>Wall calculator produces correct sqft from mm dimensions; door calculator counts doors by type; glass walls handled separately</done>
</task>

<task type="auto">
  <name>Implement room-based quantity calculators</name>
  <files>app/services/bom_calculators.py</files>
  <action>
    Add to the same module:

    3. `calculate_flooring_quantities(rooms: List[GeneratedRoom]) -> List[BOMLineItem]`:
       - For each room: area_sqm → sqft (× 10.764)
       - Use `get_material_for_room("flooring", room.room_type)` for material selection
       - Emit 1 line item per room

    4. `calculate_ceiling_quantities(rooms: List[GeneratedRoom]) -> List[BOMLineItem]`:
       - Same area as flooring (ceiling covers the same footprint)
       - Use `get_material_for_room("ceiling", room.room_type)` for material selection
       - Emit 1 line item per room

    5. `calculate_paint_quantities(walls: List[InteriorWall], perimeter_walls: List[dict], doors: List[Door], ceiling_height_mm: float) -> List[BOMLineItem]`:
       - Total wall area = all walls × height × 2 sides
       - Subtract door openings: each door × door_width × 2100mm (standard door height)
       - Convert to sqft
       - Emit 1 line item: "Interior Emulsion Paint"

    6. `calculate_electrical_quantities(rooms: List[GeneratedRoom]) -> List[BOMLineItem]`:
       - Rule: 1 electrical point per 50 sqft of room area (minimum 2 per room)
       - Emit 1 line item per room

    7. `calculate_skirting_quantities(rooms: List[GeneratedRoom]) -> List[BOMLineItem]`:
       - Calculate room perimeter from boundary polygon vertices
       - Convert mm → running feet (÷ 304.8)
       - Emit 1 line item per room: "PVC Skirting"

    Important:
    - All functions PURE — no side effects
    - Room perimeter = sum of edge lengths from boundary polygon
    - Use Shoelace or simple distance for perimeter
  </action>
  <verify>pytest tests/test_bom_calculators.py -v</verify>
  <done>All 7 calculators produce correct quantities; flooring/ceiling use room_type-based material selection; paint subtracts door openings; electrical uses per-sqft rule; skirting uses polygon perimeter</done>
</task>

<task type="auto">
  <name>Write comprehensive tests for all calculators</name>
  <files>tests/test_bom_calculators.py</files>
  <action>
    Write tests covering:

    1. **Wall calculator tests:**
       - Single wall → correct sqft for both sides
       - Glass wall → glass partition, not drywall
       - Multiple walls → sum correctly

    2. **Door calculator tests:**
       - Mix of single, double, sliding → correct counts
       - Sliding doors → glass door material

    3. **Flooring calculator tests:**
       - Office room → vitrified tiles
       - Conference room → carpet tiles
       - Unknown room type → falls back to default

    4. **Ceiling calculator tests:**
       - Similar to flooring but different material selection

    5. **Paint calculator tests:**
       - Wall area minus door openings
       - Zero doors → no subtraction

    6. **Electrical calculator tests:**
       - Small room (< 50 sqft) → minimum 2 points
       - Large room (200 sqft) → 4 points

    7. **Skirting calculator tests:**
       - Rectangular room → perimeter matches expected

    Use `GeneratedRoom` and `InteriorWall` fixtures with known dimensions for deterministic assertions.
  </action>
  <verify>pytest tests/test_bom_calculators.py -v --tb=short</verify>
  <done>All calculator tests pass with deterministic assertions on quantities</done>
</task>

## Success Criteria
- [ ] 7 calculator functions implemented, all pure (no side effects)
- [ ] Wall areas correctly account for both sides and glass exceptions
- [ ] Room-based calculators use room_type for material selection
- [ ] Paint calculator subtracts door openings
- [ ] Electrical uses 1-point-per-50sqft rule with minimum 2
- [ ] All tests pass with deterministic quantity assertions