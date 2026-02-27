---
phase: 02-bom-calculator-engine
plan: 02
type: tdd
wave: 2
depends_on: ["02-bom-calculator-engine-01"]
files_modified:
  - app/services/bom_calculator.py
  - tests/test_bom_calculator.py
autonomous: true
requirements: [BOM-01, BOM-04]

must_haves:
  truths:
    - "Wall area (height × length) drives drywall/partition quantity"
    - "Room floor area drives flooring and ceiling tile quantity"
    - "Room perimeter drives baseboard/skirting quantity"
    - "Each door generates door panel + frame + hardware line items"
    - "Bathrooms include waterproofing line items, kitchens include backsplash"
    - "Different room types produce different material lists"
    - "Grand total equals sum of all line item amounts"
  artifacts:
    - path: "app/services/bom_calculator.py"
      provides: "Deterministic BOM calculation from layout geometry"
      exports: ["calculate_bom"]
      min_lines: 100
    - path: "tests/test_bom_calculator.py"
      provides: "Comprehensive tests for geometry-to-BOM calculation"
      min_lines: 100
  key_links:
    - from: "app/services/bom_calculator.py"
      to: "app/models/layout.py"
      via: "Reads GeneratedRoom.boundary for area/perimeter, InteriorWall for wall lengths, Door for door counts"
      pattern: "GeneratedLayout|GeneratedRoom|InteriorWall|Door"
    - from: "app/services/bom_calculator.py"
      to: "app/models/bom.py"
      via: "Returns BOMResult with BOMLineItem list"
      pattern: "BOMResult|BOMLineItem"
    - from: "app/services/bom_calculator.py"
      to: "app/models/bom.py"
      via: "Uses ROOM_TYPE_MATERIALS for room-type-specific material rules"
      pattern: "ROOM_TYPE_MATERIALS|BASE_ROOM_CATEGORIES"
---

<objective>
Build the deterministic BOM calculator that converts layout geometry into priced material line items using TDD.

Purpose: This is the core value proposition — geometry goes in, a priced bill of materials comes out. Every quantity must be geometrically derivable (wall area → drywall sqft, floor area → tiles sqft, perimeter → skirting running_foot, door count → door pieces). Room-type rules add specialty items (bathroom → waterproofing, server room → raised flooring).

Output: `app/services/bom_calculator.py` with `calculate_bom(layout, materials)` function, fully tested via `tests/test_bom_calculator.py`.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-bom-calculator-engine/02-bom-calculator-engine-01-SUMMARY.md

@app/models/layout.py
@app/models/bom.py

<interfaces>
<!-- Contracts created by Plan 01 that this plan implements against -->

From app/models/layout.py:
```python
class GeneratedRoom(BaseModel):
    name: str                              # "Reception", "Bathroom 1"
    room_type: str                         # "reception", "bathroom", "server_room"
    boundary: list[tuple[float, float]]    # Closed polygon vertices in mm
    area_sqm: float                        # Room area in square meters

class InteriorWall(BaseModel):
    id: str
    x1: float; y1: float; x2: float; y2: float  # coordinates in mm
    thickness_mm: float = 100.0
    material: str = "drywall"

class Door(BaseModel):
    id: str; wall_id: str
    width_mm: float
    door_type: Literal["single", "double", "sliding"]

class GeneratedLayout(BaseModel):
    rooms: list[GeneratedRoom]
    interior_walls: list[InteriorWall]
    doors: list[Door]
    fixtures: list[Fixture]
    page_dimensions_mm: tuple[float, float]
    perimeter_walls: list[dict]
```

From app/models/bom.py (created in Plan 01):
```python
class MaterialInfo(BaseModel):
    material_name: str
    category: str
    unit_of_measurement: str
    cost_inr: float

class BOMLineItem(BaseModel):
    material_name: str; category: str
    quantity: float; unit: str
    rate_inr: float; amount_inr: float
    room_name: Optional[str]; notes: Optional[str]

class BOMResult(BaseModel):
    line_items: list[BOMLineItem]
    grand_total_inr: float
    room_count: int
    total_area_sqm: float

ROOM_TYPE_MATERIALS: dict[str, list[str]]  # room_type -> extra categories
BASE_ROOM_CATEGORIES: list[str]  # ["flooring", "ceiling", "paint", "electrical", "baseboard"]
DEFAULT_CEILING_HEIGHT_MM: float = 2700.0
SQM_TO_SQFT: float = 10.764
MM_TO_M: float = 0.001
```
</interfaces>
</context>

<feature>
  <name>Deterministic BOM Calculator</name>
  <files>app/services/bom_calculator.py, tests/test_bom_calculator.py</files>
  <behavior>
    The calculator is a PURE FUNCTION: `calculate_bom(layout: GeneratedLayout, materials: list[MaterialInfo]) -> BOMResult`

    NO database calls, NO AI, NO side effects. Materials are passed in as a list (the caller loads them from DB or provides test fixtures).

    **Geometry-to-quantity rules (deterministic):**

    1. **Walls** — For each InteriorWall, compute wall length (Euclidean distance x1,y1→x2,y2) and wall area (length × ceiling_height). Convert to sqft. Look up the first material matching the wall's `material` field in the `wall` category. Generate a BOMLineItem.

    2. **Flooring** — For each GeneratedRoom, use area_sqm converted to sqft. Pick the first `flooring` category material. Generate a BOMLineItem tagged with room_name.

    3. **Ceiling** — Same area as flooring. Pick the first `ceiling` category material. Generate a BOMLineItem.

    4. **Paint** — Wall paint: compute total wall area for each room (sum of interior wall areas touching that room, or approximate as room perimeter × ceiling_height). Use the first `paint` category material. Two coats → multiply quantity by 2. Add primer as a separate line item.

    5. **Baseboard/Skirting** — Room perimeter (computed from boundary polygon) in running_foot. Pick the first `baseboard` category material.

    6. **Doors** — For each Door, generate line items: 1 door panel (from `door` category, match door_type to appropriate material), 1 door frame (from `door_hardware` category, quantity = frame perimeter in running_foot estimated as (door_width + ceiling_height*0.8) * 2 / 304.8 for a standard 2.1m height), 1 handle set, 1 closer.

    7. **Electrical** — Per room: estimate light points based on area (1 per 4 sqm), power sockets (1 per 3 sqm, min 2), 1 switch board per room.

    8. **Room-type specialties** — If room_type is in ROOM_TYPE_MATERIALS, add extra categories:
       - bathroom/washroom → waterproofing (floor area + wall area up to 1.5m height)
       - kitchen/pantry → backsplash (specialty, wall area up to 600mm above counter)
       - server_room → raised access flooring (specialty, replace standard flooring)

    **Test cases (input → expected output):**

    Case 1: Single 3m×4m office room, 1 drywall wall (3m), 1 single door
    → flooring: 12 sqm ≈ 129.2 sqft
    → ceiling: same area
    → baseboard: perimeter 14m ≈ 45.9 running_foot
    → 1 wall line item: 3m × 2.7m = 8.1 sqm ≈ 87.2 sqft
    → 1 door panel, 1 frame, 1 handle, 1 closer
    → electrical: 3 light points, 4 sockets, 1 switchboard
    → paint: wall area × 2 coats + primer

    Case 2: Bathroom (3m×2m) — same as Case 1 PLUS waterproofing line items

    Case 3: Two rooms with different types — office + bathroom — verify different material lists

    Case 4: Empty layout (no rooms) → BOMResult with empty line_items, grand_total=0

    Case 5: Grand total = sum of all line_item.amount_inr values
  </behavior>
  <implementation>
    Create `app/services/bom_calculator.py` with:

    ```python
    def calculate_bom(
        layout: GeneratedLayout,
        materials: list[MaterialInfo],
        ceiling_height_mm: float = DEFAULT_CEILING_HEIGHT_MM,
    ) -> BOMResult:
    ```

    Internal helper functions (all pure, testable):
    - `_wall_length_mm(wall: InteriorWall) -> float` — Euclidean distance
    - `_room_perimeter_mm(boundary: list[tuple[float, float]]) -> float` — sum of polygon edge lengths
    - `_find_material(materials: list[MaterialInfo], category: str, preference: str = "") -> Optional[MaterialInfo]` — find first material in category, optionally preferring a name substring match
    - `_sqm_to_sqft(sqm: float) -> float`
    - `_mm_to_running_foot(mm: float) -> float`
    - `_calculate_room_bom(room, materials, ceiling_height_mm) -> list[BOMLineItem]`
    - `_calculate_wall_bom(wall, materials, ceiling_height_mm) -> list[BOMLineItem]`
    - `_calculate_door_bom(door, materials) -> list[BOMLineItem]`
    - `_calculate_electrical(room, materials) -> list[BOMLineItem]`
    - `_calculate_specialty(room, materials, ceiling_height_mm) -> list[BOMLineItem]`

    Each helper returns a list of BOMLineItems. The main function aggregates and computes grand_total as sum of all amounts.

    IMPORTANT: Do NOT import or call any database/repository functions. The calculator is pure.
  </implementation>
</feature>

<verification>
1. `pytest tests/test_bom_calculator.py -v` — all calculator tests pass
2. `pytest tests/ -x --timeout=60` — no regressions in existing tests
</verification>

<success_criteria>
- calculate_bom() converts layout geometry to priced BOM line items deterministically
- Wall area drives wall material quantity, floor area drives flooring, perimeter drives baseboard
- Bathrooms produce waterproofing items that offices don't
- Grand total equals sum of all line item amounts
- All quantities use correct units (sqft, running_foot, piece)
- Tests cover: single room, bathroom specialty, multi-room, empty layout, grand total correctness
</success_criteria>

<output>
After completion, create `.planning/phases/02-bom-calculator-engine/02-bom-calculator-engine-02-SUMMARY.md`
</output>
