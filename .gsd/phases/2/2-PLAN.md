---
phase: 2
plan: 2
wave: 2
---

# Plan 2.2: Constraint Validation & Grid Snapping

## Objective

Ensure generated layouts are construction-ready by snapping all coordinates to a 50mm construction grid and validating spatial constraints using Shapely. This plan builds the "critic" half of the generate-validate loop — it takes a raw GeneratedLayout and either approves it or produces a list of specific, actionable violations that can be fed back to the generator for correction.

## Context

- .gsd/SPEC.md (50mm grid requirement, constraint requirements)
- .gsd/RESEARCH.md (Section 2: The Critic — Shapely polygon intersection, buffer operations, arc-polygon intersection)
- app/models/layout.py (Plan 2.1 — GeneratedLayout, InteriorWall, Door, Fixture)
- app/models/spatial.py (SpatialGraph — perimeter reference)

## Tasks

<task type="auto">
  <name>Implement 50mm construction grid snapping</name>
  <files>
    app/services/grid_snapper.py
    tests/test_grid_snapper.py
  </files>
  <action>
    1. Create app/services/grid_snapper.py:

       - snap_to_grid(value: float, grid_mm: int = 50) -> float
         - Round a single coordinate to nearest grid increment
         - Example: 1723 → 1700, 1749 → 1750, 1750 → 1750

       - snap_layout_to_grid(layout: GeneratedLayout, grid_mm: int = 50) -> GeneratedLayout
         - Snap all coordinates in the layout to the grid:
           - InteriorWall: x1, y1, x2, y2
           - Door: no coordinate snapping needed (position_along_wall is relative 0-1)
           - Fixture: center_x, center_y, width_mm, depth_mm
           - GeneratedRoom: all boundary polygon vertices
         - Recalculate room areas after snapping (shoelace formula on snapped boundary)
         - Return a new GeneratedLayout (do not mutate the original)

       - Preserve wall connectivity after snapping:
         - If two walls shared an endpoint before snapping, they must share it after
         - This is naturally handled by snapping to the same grid — endpoints at (1001, 2003) and (1001, 2003) both snap to (1000, 2000)
         - But warn in docstring: walls that were close but NOT connected may merge after snapping

    2. tests/test_grid_snapper.py:
       - Test snap_to_grid with edge cases: exact multiples, midpoints, negative values
       - Test snap_layout_to_grid: verify all coordinates in output are multiples of 50
       - Test that room areas are recalculated after snapping
       - Test that the original layout is not mutated (immutability)

    Do NOT:
    - Snap door position_along_wall — it's a ratio (0-1), not a coordinate
    - Add wall merging or deduplication — that's a constraint check, not a snap operation
    - Handle coordinate system conversion — that was done in Plan 2.1's generation service
  </action>
  <verify>
    pytest tests/test_grid_snapper.py -v
  </verify>
  <done>
    - All coordinates in snapped layout are exact multiples of grid_mm
    - Room areas recalculated via shoelace formula
    - Original layout is not mutated
    - Tests pass for edge cases (exact multiples, midpoints, zero)
  </done>
</task>

<task type="auto">
  <name>Build Shapely-based constraint validator</name>
  <files>
    app/services/constraint_checker.py
    app/models/constraints.py
    tests/test_constraint_checker.py
  </files>
  <action>
    1. Create app/models/constraints.py:

       - ConstraintViolationType: Enum with values:
         - ROOM_OVERLAP — two rooms share area
         - CORRIDOR_TOO_NARROW — corridor/passage width < 900mm
         - DOOR_SWING_BLOCKED — door arc intersects wall or fixture
         - ROOM_NOT_ENCLOSED — room boundary polygon is not valid/closed
         - AREA_EXCEEDS_PERIMETER — total room area exceeds available perimeter area
         - FIXTURE_OUTSIDE_ROOM — fixture center is outside its assigned room polygon
         - FIXTURE_OVERLAP — two fixtures in the same room overlap

       - ConstraintViolation:
         - type: ConstraintViolationType
         - description: str (human-readable, e.g. "Operatory 1 and Operatory 2 overlap by 2.3 sqm")
         - severity: Literal["error", "warning"] (errors block acceptance, warnings are informational)
         - affected_elements: list[str] (IDs of involved walls/doors/fixtures/rooms)

       - ConstraintResult:
         - passed: bool (True if zero errors; warnings are OK)
         - violations: list[ConstraintViolation]
         - summary: str (e.g. "2 errors, 1 warning")

    2. Create app/services/constraint_checker.py:

       - validate_layout(layout: GeneratedLayout) -> ConstraintResult

       - Check 1: Room overlap detection
         - Convert each GeneratedRoom.boundary to a Shapely Polygon
         - For each pair of rooms, check intersection area
         - If intersection.area > 0.01 sqm (tolerance for snapping artifacts): ERROR

       - Check 2: Corridor minimum width
         - For rooms with room_type == "corridor" or "hallway"
         - Use Shapely: polygon.buffer(-450) (negative buffer by half of 900mm minimum)
         - If result is empty → corridor is narrower than 900mm at some point: ERROR

       - Check 3: Door swing clearance
         - For each Door, calculate the swing arc using a helper:
           def get_door_swing_arc(wall: InteriorWall, door: Door) -> Polygon:
             # 1. Interpolate hinge point on wall line at door.position_along_wall
             #    hinge = wall_start + position_along_wall * (wall_end - wall_start)
             # 2. Determine swing side from door.swing_direction ("left"/"right" relative to wall direction)
             # 3. Create quarter-circle arc: Point(hinge).buffer(door.width_mm).intersection(sector)
             #    where sector is a wedge polygon covering the 90° swing range
             # 4. Return arc as Shapely Polygon (tessellated, ~32 segments)
         - For "sliding" doors, skip swing check entirely (no arc)
         - Check arc polygon against all nearby walls and fixtures using Shapely intersection
         - If intersection area > 0: ERROR

       - Check 4: Room enclosure
         - For each GeneratedRoom, check Shapely Polygon(boundary).is_valid
         - If not valid (self-intersecting, unclosed): ERROR

       - Check 5: Area budget
         - Sum all room areas; compare to perimeter bounding box area
         - If sum > perimeter area * 1.05 (5% tolerance): ERROR

       - Check 6: Fixture containment
         - For each Fixture, check if Point(center_x, center_y) is within its assigned room polygon
         - If not: WARNING (fixtures near walls might be slightly outside due to snapping)

       - Check 7: Fixture overlap
         - For fixtures in the same room, create bounding box rectangles and check pairwise intersection
         - If intersection area > 0: WARNING

       - Return ConstraintResult with all violations collected

    3. tests/test_constraint_checker.py:
       - Test valid layout: two non-overlapping rectangular rooms → passes
       - Test overlapping rooms: two rooms sharing a region → error detected
       - Test narrow corridor: 600mm wide corridor → error detected
       - Test door swing blocked by wall → error detected
       - Test fixture outside room → warning detected
       - Test that warnings don't cause failure (passed=True with warnings only)

    Do NOT:
    - Attempt to FIX violations — the checker only reports. Fixing happens in Plan 2.3's feedback loop
    - Add constraint configuration (configurable thresholds) — hardcode MVP values
    - Handle curved walls — MVP is straight segments only
  </action>
  <verify>
    pytest tests/test_constraint_checker.py -v
  </verify>
  <done>
    - validate_layout() checks all 7 constraint types
    - Returns ConstraintResult with typed violations, descriptions, and severity
    - Errors block acceptance; warnings are informational
    - Shapely correctly detects overlaps, narrow corridors, and door swing collisions
    - All tests pass
  </done>
</task>

## Success Criteria

- [ ] Grid snapper rounds all layout coordinates to 50mm multiples
- [ ] Room areas recalculated after snapping
- [ ] Constraint checker validates 7 spatial rules using Shapely
- [ ] Violations include human-readable descriptions suitable for LLM feedback
- [ ] Error vs. warning severity correctly distinguishes blocking vs. informational issues
- [ ] All tests pass
