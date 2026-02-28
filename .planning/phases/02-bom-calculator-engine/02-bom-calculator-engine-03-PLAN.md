---
phase: 02-bom-calculator-engine
plan: 03
type: execute
wave: 2
depends_on: ["02-bom-calculator-engine-01", "02-bom-calculator-engine-02"]
files_modified:
  - app/services/job_runner.py
  - tests/test_bom_integration.py
autonomous: true
requirements: [BOM-05]

must_haves:
  truths:
    - "Generate job produces a BOM with non-zero total_cost_inr stored in the database"
    - "BOM bom_data contains line_items array with material_name, quantity, unit, rate_inr, amount_inr for each item"
    - "Different room types in the layout produce different material line items in the BOM"
    - "Status endpoint shows generation_summary with non-zero total_cost_inr"
  artifacts:
    - path: "app/services/job_runner.py"
      provides: "Integration of BOM calculator into generate job pipeline"
      contains: "calculate_bom"
    - path: "tests/test_bom_integration.py"
      provides: "Integration tests verifying end-to-end BOM calculation from layout"
      min_lines: 60
  key_links:
    - from: "app/services/job_runner.py"
      to: "app/services/bom_calculator.py"
      via: "Calls calculate_bom(layout, materials) after successful generation"
      pattern: "calculate_bom"
    - from: "app/services/job_runner.py"
      to: "app/services/materials_repository.py"
      via: "Loads materials from DB to pass into calculator"
      pattern: "get_all_materials"
    - from: "app/services/job_runner.py"
      to: "app/services/bom_repository.py"
      via: "Persists calculated BOM with real total_cost_inr (not 0.0)"
      pattern: "create_bom.*total_cost_inr"
---

<objective>
Wire the BOM calculator into the generation pipeline so the generate endpoint returns a fully priced BOM instead of `total_cost_inr=0.0`.

Purpose: This closes the loop — BOM-05 requires that the generate endpoint returns a real priced BOM. Currently `_run_generate_job` in `job_runner.py` stores `total_cost_inr=0.0` with raw layout data. After this plan, it calls `calculate_bom()` on the generated layout, stores the priced line items, and persists the real total.

Output: Updated `job_runner.py` with BOM calculation integrated, plus integration tests that verify the full pipeline produces priced BOMs.
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
@.planning/phases/02-bom-calculator-engine/02-bom-calculator-engine-02-SUMMARY.md

@app/services/job_runner.py
@app/services/bom_repository.py
@app/api/routes.py

<interfaces>
<!-- Contracts from Plan 01 and Plan 02 that this plan wires together -->

From app/services/bom_calculator.py (created in Plan 02):
```python
def calculate_bom(
    layout: GeneratedLayout,
    materials: list[MaterialInfo],
    ceiling_height_mm: float = DEFAULT_CEILING_HEIGHT_MM,
) -> BOMResult:
    """Pure function: layout geometry + materials catalog → priced BOM."""
```

From app/models/bom.py (created in Plan 01):
```python
class MaterialInfo(BaseModel):
    material_name: str
    category: str
    unit_of_measurement: str
    cost_inr: float

class BOMResult(BaseModel):
    line_items: list[BOMLineItem]
    grand_total_inr: float
    room_count: int
    total_area_sqm: float

class BOMLineItem(BaseModel):
    material_name: str; category: str
    quantity: float; unit: str
    rate_inr: float; amount_inr: float
    room_name: Optional[str]; notes: Optional[str]
```

From app/services/materials_repository.py (created in Plan 01):
```python
def get_all_materials() -> list[dict]:
    """Load all materials from the pricing catalog."""
```

From app/services/bom_repository.py (existing):
```python
def create_bom(floorplan_id: int, total_cost_inr: float, bom_data: Optional[Dict] = None) -> int
```

From app/services/job_runner.py (existing _run_generate_job):
```python
# Currently stores total_cost_inr=0.0 and raw layout data
bom_data = {
    "success": result.success,
    "iterations_used": result.iterations_used,
    "constraint_result": latest_constraint,
    "layout": result.layout.to_json(),
    "prompt": prompt,
}
bom_id = create_bom(floorplan_id=floorplan_id, total_cost_inr=0.0, bom_data=bom_data)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Integrate BOM calculator into generate job runner</name>
  <files>app/services/job_runner.py</files>
  <action>
Modify `_run_generate_job()` in `app/services/job_runner.py` to calculate a real BOM after successful layout generation.

**Changes to `_run_generate_job()`:**

After `result = generate_validated_layout(...)` succeeds and `result.layout is not None`:

1. Load materials from DB:
```python
from app.services.materials_repository import get_all_materials
from app.models.bom import MaterialInfo, BOMResult
from app.services.bom_calculator import calculate_bom

raw_materials = get_all_materials()
materials = [MaterialInfo(**m) for m in raw_materials]
```

2. Calculate BOM:
```python
bom_result = calculate_bom(layout=result.layout, materials=materials)
```

3. Update the `bom_data` dict to include the calculated line items alongside the existing layout/constraint data:
```python
bom_data = {
    "success": result.success,
    "iterations_used": result.iterations_used,
    "constraint_result": latest_constraint,
    "layout": result.layout.to_json(),
    "prompt": prompt,
    "line_items": [item.model_dump(mode="json") for item in bom_result.line_items],
    "room_count": bom_result.room_count,
    "total_area_sqm": bom_result.total_area_sqm,
}
```

4. Change `total_cost_inr=0.0` to `total_cost_inr=bom_result.grand_total_inr` in the `create_bom()` call.

5. **Error handling:** If `get_all_materials()` raises (DB unreachable) or `calculate_bom()` raises, log a warning and fall back to the current behavior (total_cost_inr=0.0, no line_items). The BOM calculation must NOT block the layout result from being persisted. Wrap the BOM calculation in a try/except:
```python
try:
    raw_materials = get_all_materials()
    materials = [MaterialInfo(**m) for m in raw_materials]
    bom_result = calculate_bom(layout=result.layout, materials=materials)
    total_cost = bom_result.grand_total_inr
    bom_data["line_items"] = [item.model_dump(mode="json") for item in bom_result.line_items]
    bom_data["room_count"] = bom_result.room_count
    bom_data["total_area_sqm"] = bom_result.total_area_sqm
except Exception as calc_exc:
    logger.warning("BOM calculation failed, storing layout without pricing: %s", calc_exc)
    total_cost = 0.0
```

Then use `total_cost` in the `create_bom()` call.

**Do NOT change the function signature or the result_ref structure.** Only change how bom_data and total_cost_inr are computed inside the existing success path.
  </action>
  <verify>
    <automated>python -c "from app.services.job_runner import _run_generate_job; print('job_runner imports OK — calculate_bom integrated')"</automated>
  </verify>
  <done>_run_generate_job calls calculate_bom() on successful layouts, stores real total_cost_inr and line_items in bom_data. Falls back gracefully to 0.0 if BOM calculation fails.</done>
</task>

<task type="auto">
  <name>Task 2: Add integration tests for BOM pipeline</name>
  <files>tests/test_bom_integration.py</files>
  <action>
Create `tests/test_bom_integration.py` with integration tests that verify the BOM calculator produces correct output when wired to a realistic layout.

These tests do NOT require a database or Gemini API — they test `calculate_bom()` with fixture data that mimics what `_run_generate_job` would produce.

**Test fixtures (at module level):**

1. `sample_materials()` — Returns a list of ~10 `MaterialInfo` objects covering all major categories (wall, flooring, ceiling, paint, electrical, baseboard, door, door_hardware, waterproofing, specialty). Use realistic ₹ rates.

2. `office_layout()` — Returns a `GeneratedLayout` with:
   - 2 rooms: "Reception" (office, 4m×5m=20sqm), "Meeting Room" (meeting_room, 3m×4m=12sqm)
   - 2 interior walls (one 5m, one 4m, both drywall)
   - 2 doors (1 single, 1 sliding)
   - page_dimensions_mm=(10000, 8000)

3. `bathroom_layout()` — Returns a `GeneratedLayout` with:
   - 1 room: "Bathroom 1" (bathroom, 2m×3m=6sqm)
   - 1 interior wall (3m)
   - 1 door (single)

**Tests:**

```python
def test_office_bom_has_all_base_categories(sample_materials, office_layout):
    """Office rooms produce flooring, ceiling, paint, electrical, baseboard items."""
    result = calculate_bom(office_layout, sample_materials)
    categories = {item.category for item in result.line_items}
    assert "flooring" in categories
    assert "ceiling" in categories
    assert "paint" in categories
    assert "electrical" in categories
    assert "baseboard" in categories
    assert "wall" in categories
    assert "waterproofing" not in categories  # office has no waterproofing

def test_bathroom_includes_waterproofing(sample_materials, bathroom_layout):
    """Bathroom rooms produce waterproofing line items."""
    result = calculate_bom(bathroom_layout, sample_materials)
    categories = {item.category for item in result.line_items}
    assert "waterproofing" in categories

def test_different_room_types_produce_different_materials(sample_materials, office_layout, bathroom_layout):
    """Office and bathroom produce different material lists."""
    office_result = calculate_bom(office_layout, sample_materials)
    bathroom_result = calculate_bom(bathroom_layout, sample_materials)
    office_categories = {item.category for item in office_result.line_items}
    bathroom_categories = {item.category for item in bathroom_result.line_items}
    assert bathroom_categories - office_categories  # bathroom has extras

def test_grand_total_equals_sum_of_amounts(sample_materials, office_layout):
    """Grand total must equal sum of all line item amounts."""
    result = calculate_bom(office_layout, sample_materials)
    expected_total = sum(item.amount_inr for item in result.line_items)
    assert abs(result.grand_total_inr - expected_total) < 0.01

def test_wall_quantity_is_geometrically_correct(sample_materials, office_layout):
    """Wall material quantity should reflect wall area (length × height)."""
    result = calculate_bom(office_layout, sample_materials)
    wall_items = [i for i in result.line_items if i.category == "wall"]
    assert len(wall_items) > 0
    # 5m + 4m walls at 2.7m height = 24.3 sqm ≈ 261.6 sqft total
    total_wall_sqft = sum(i.quantity for i in wall_items)
    assert total_wall_sqft > 200  # reasonable range
    assert total_wall_sqft < 350

def test_flooring_quantity_matches_room_area(sample_materials, office_layout):
    """Flooring quantity should match total room floor area."""
    result = calculate_bom(office_layout, sample_materials)
    flooring_items = [i for i in result.line_items if i.category == "flooring"]
    total_flooring_sqft = sum(i.quantity for i in flooring_items)
    # 20 + 12 = 32 sqm ≈ 344.4 sqft
    assert total_flooring_sqft > 300
    assert total_flooring_sqft < 400

def test_empty_layout_produces_empty_bom(sample_materials):
    """Layout with no rooms produces empty BOM with zero total."""
    from app.models.layout import GeneratedLayout
    empty = GeneratedLayout(
        rooms=[], interior_walls=[], doors=[], fixtures=[],
        grid_size_mm=50, prompt="test", perimeter_walls=[],
        page_dimensions_mm=(10000, 8000)
    )
    result = calculate_bom(empty, sample_materials)
    assert result.grand_total_inr == 0.0
    assert len(result.line_items) == 0

def test_each_door_generates_multiple_items(sample_materials, office_layout):
    """Each door should generate door panel + hardware line items."""
    result = calculate_bom(office_layout, sample_materials)
    door_items = [i for i in result.line_items if i.category in ("door", "door_hardware")]
    # 2 doors × (panel + frame + handle + closer) = 8 items minimum
    assert len(door_items) >= 4  # at minimum 2 panels + 2 hardware

def test_bom_result_has_correct_room_count(sample_materials, office_layout):
    """BOM result room_count matches layout room count."""
    result = calculate_bom(office_layout, sample_materials)
    assert result.room_count == 2

def test_amount_equals_quantity_times_rate(sample_materials, office_layout):
    """Each line item's amount must equal quantity × rate."""
    result = calculate_bom(office_layout, sample_materials)
    for item in result.line_items:
        expected = round(item.quantity * item.rate_inr, 2)
        assert abs(item.amount_inr - expected) < 0.01, (
            f"{item.material_name}: {item.quantity} × {item.rate_inr} = "
            f"{expected}, got {item.amount_inr}"
        )
```

Use pytest fixtures (`@pytest.fixture`) for sample_materials, office_layout, and bathroom_layout.
  </action>
  <verify>
    <automated>pytest tests/test_bom_integration.py -v --timeout=30</automated>
  </verify>
  <done>All integration tests pass. Tests verify: base categories for offices, waterproofing for bathrooms, different room types produce different materials, grand total correctness, geometric quantity accuracy, empty layout handling, door item generation, amount = quantity × rate.</done>
</task>

</tasks>

<verification>
1. `pytest tests/test_bom_integration.py -v` — all integration tests pass
2. `pytest tests/test_bom_calculator.py -v` — calculator unit tests still pass
3. `pytest tests/ -x --timeout=60` — no regressions in existing test suite
4. `python -c "from app.services.job_runner import _run_generate_job; print('Integration wired')"` — import check
</verification>

<success_criteria>
- _run_generate_job produces BOM with real total_cost_inr (not 0.0) when materials are available
- bom_data includes line_items array with priced materials
- BOM calculation failure is non-blocking (graceful fallback to 0.0)
- Integration tests verify geometry → priced BOM for office and bathroom layouts
- All existing tests continue passing
</success_criteria>

<output>
After completion, create `.planning/phases/02-bom-calculator-engine/02-bom-calculator-engine-03-SUMMARY.md`
</output>
