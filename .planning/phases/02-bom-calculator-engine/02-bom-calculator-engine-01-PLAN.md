---
phase: 02-bom-calculator-engine
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/models/bom.py
  - app/models/database.py
  - scripts/setup_supabase_schema.py
  - app/services/materials_repository.py
autonomous: true
requirements: [BOM-02, BOM-03]

must_haves:
  truths:
    - "Materials pricing table has ~45 real Indian market items across wall, flooring, ceiling, door, paint, electrical, waterproofing, and specialty categories"
    - "BOM domain models define line items with material name, category, quantity, unit, rate (₹), amount (₹)"
    - "Materials can be loaded from the database by category for use in BOM calculation"
  artifacts:
    - path: "app/models/bom.py"
      provides: "BOM domain types — BOMLineItem, BOMResult, MaterialInfo, room-type rules"
      exports: ["BOMLineItem", "BOMResult", "MaterialInfo", "MaterialCategory", "ROOM_TYPE_MATERIALS", "BASE_ROOM_CATEGORIES", "DEFAULT_CEILING_HEIGHT_MM"]
    - path: "app/models/database.py"
      provides: "MaterialPricing with category field"
      contains: "category: str"
    - path: "scripts/setup_supabase_schema.py"
      provides: "Expanded materials seed (~45 items with categories)"
      min_lines: 200
    - path: "app/services/materials_repository.py"
      provides: "DB access for material pricing catalog"
      exports: ["get_all_materials", "get_materials_by_category"]
  key_links:
    - from: "app/services/materials_repository.py"
      to: "app/models/database.py"
      via: "SQLModel query on MaterialPricing"
      pattern: "select\\(MaterialPricing\\)"
    - from: "app/models/bom.py"
      to: "app/models/bom.py"
      via: "ROOM_TYPE_MATERIALS dict maps room_type strings to category lists"
      pattern: "ROOM_TYPE_MATERIALS"
---

<objective>
Create BOM domain types and expand the materials pricing catalog from 10 to ~45 items with category classification.

Purpose: Establish the type contracts and data foundation that the BOM calculator (Plan 02) will compute against. Without typed BOM models, the calculator has no output contract. Without categorized materials, the calculator can't match geometry to pricing.

Output: `app/models/bom.py` with all BOM types, updated `MaterialPricing` model with `category` field, expanded seed script with ~45 materials, and `materials_repository.py` for DB access.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@app/models/database.py
@app/models/layout.py
@app/services/bom_repository.py
@app/core/config.py
@scripts/setup_supabase_schema.py

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From app/models/database.py:
```python
class MaterialPricing(SQLModel, table=True):
    __tablename__ = "materials_pricing"
    id: Optional[int] = Field(default=None, primary_key=True)
    material_name: str
    unit_of_measurement: str  # sqft, running_foot, piece, etc.
    cost_inr: float  # Cost in Indian Rupees
```

From app/models/layout.py:
```python
class GeneratedRoom(BaseModel):
    name: str
    room_type: str
    boundary: list[tuple[float, float]]  # Closed polygon vertices in mm
    area_sqm: float

class InteriorWall(BaseModel):
    id: str
    x1: float; y1: float; x2: float; y2: float  # mm
    thickness_mm: float = 100.0
    material: str = "drywall"

class Door(BaseModel):
    id: str; wall_id: str
    width_mm: float
    door_type: Literal["single", "double", "sliding"]
```

From app/services/bom_repository.py:
```python
def create_bom(floorplan_id: int, total_cost_inr: float, bom_data: Optional[Dict] = None) -> int
def update_bom_data(bom_id: int, total_cost_inr: float, bom_data: Dict) -> bool
```

From app/core/database.py:
```python
def get_session() -> Generator[Session, None, None]  # context manager
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create BOM domain models and add category to MaterialPricing</name>
  <files>app/models/bom.py, app/models/database.py</files>
  <action>
Create `app/models/bom.py` with the following types:

1. **MaterialCategory** — `str, Enum` with values: `wall`, `flooring`, `ceiling`, `door`, `door_hardware`, `paint`, `electrical`, `baseboard`, `waterproofing`, `specialty`. These are the categories that materials belong to and that the BOM calculator will match against geometry.

2. **MaterialInfo** — Plain Pydantic BaseModel (NOT SQLModel) used as calculator input. Fields: `material_name: str`, `category: str`, `unit_of_measurement: str` (sqft, running_foot, piece, sqm, liter), `cost_inr: float`. This decouples the calculator from the DB model.

3. **BOMLineItem** — Pydantic BaseModel for a single priced material line. Fields: `material_name: str`, `category: str`, `quantity: float` (in the material's unit), `unit: str`, `rate_inr: float`, `amount_inr: float` (quantity × rate_inr), `room_name: Optional[str] = None` (which room triggered this item), `notes: Optional[str] = None`.

4. **BOMResult** — Pydantic BaseModel for the full BOM output. Fields: `line_items: list[BOMLineItem]`, `grand_total_inr: float`, `room_count: int`, `total_area_sqm: float`.

5. **Constants:**
   - `DEFAULT_CEILING_HEIGHT_MM: float = 2700.0` — standard commercial ceiling height in India (9 ft)
   - `SQM_TO_SQFT: float = 10.764` — conversion factor
   - `M_TO_FT: float = 3.281` — meters to feet conversion
   - `MM_TO_M: float = 0.001`

6. **Room-type rules** — Dict mapping room_type strings to lists of additional material categories:
   ```python
   ROOM_TYPE_MATERIALS: dict[str, list[str]] = {
       "bathroom": ["waterproofing"],
       "washroom": ["waterproofing"],
       "restroom": ["waterproofing"],
       "toilet": ["waterproofing"],
       "kitchen": ["specialty"],  # backsplash
       "pantry": ["specialty"],   # backsplash
       "server_room": ["specialty"],  # raised flooring
       "server": ["specialty"],
       "lab": ["specialty"],
   }
   ```

7. **Base categories** applied to every room:
   ```python
   BASE_ROOM_CATEGORIES: list[str] = ["flooring", "ceiling", "paint", "electrical", "baseboard"]
   BASE_WALL_CATEGORIES: list[str] = ["wall"]
   BASE_DOOR_CATEGORIES: list[str] = ["door", "door_hardware"]
   ```

In `app/models/database.py`, add a `category` field to `MaterialPricing`:
```python
category: str = Field(default="uncategorized")  # wall, flooring, ceiling, etc.
```
Add it after `cost_inr`. The default ensures backward compatibility with any existing rows.
  </action>
  <verify>
    <automated>python -c "from app.models.bom import BOMLineItem, BOMResult, MaterialInfo, MaterialCategory, ROOM_TYPE_MATERIALS, BASE_ROOM_CATEGORIES, DEFAULT_CEILING_HEIGHT_MM, SQM_TO_SQFT; item = BOMLineItem(material_name='test', category='wall', quantity=10.0, unit='sqft', rate_inr=45.0, amount_inr=450.0); result = BOMResult(line_items=[item], grand_total_inr=450.0, room_count=1, total_area_sqm=10.0); print(f'BOMLineItem OK, BOMResult OK, categories={len(MaterialCategory)}, room_rules={len(ROOM_TYPE_MATERIALS)}')"</automated>
  </verify>
  <done>All BOM domain types import and instantiate correctly. MaterialPricing has a category field. Room-type rules map at least 5 room types to additional material categories. Unit conversion constants are defined.</done>
</task>

<task type="auto">
  <name>Task 2: Expand materials seed data and create materials repository</name>
  <files>scripts/setup_supabase_schema.py, app/services/materials_repository.py</files>
  <action>
**Materials Repository** — Create `app/services/materials_repository.py` following the existing repository pattern (see `bom_repository.py`, `floorplan_repository.py`):

```python
def get_all_materials() -> list[dict]:
    """Load all materials from the pricing catalog."""
    # SELECT * FROM materials_pricing
    # Return list of dicts with keys: id, material_name, category, unit_of_measurement, cost_inr

def get_materials_by_category(category: str) -> list[dict]:
    """Load materials filtered by category."""
    # SELECT * FROM materials_pricing WHERE category = :category
```

Use `get_session()` from `app.core.database`, query `MaterialPricing`, return typed dicts matching the repository convention.

**Seed Data Expansion** — Update `DEFAULT_MATERIALS` in `scripts/setup_supabase_schema.py` from 10 items to ~45 items. Each item must now include a `category` field. Organize by category:

**Wall (7 items):**
- Standard Gypsum Drywall (12mm) — sqft — ₹45 — wall
- Moisture-Resistant Drywall (12mm) — sqft — ₹65 — wall
- Tempered Glass Partition (10mm) — sqft — ₹350 — wall
- Laminated Glass Partition (12mm) — sqft — ₹450 — wall
- AAC Block Partition (100mm) — sqft — ₹55 — wall
- Cement Board Partition (8mm) — sqft — ₹40 — wall
- Brick Partition (100mm) — sqft — ₹60 — wall

**Flooring (8 items):**
- Vitrified Tiles (600x600mm) — sqft — ₹85 — flooring
- Ceramic Floor Tiles (300x300mm) — sqft — ₹55 — flooring
- Premium Vinyl Flooring (2mm) — sqft — ₹120 — flooring
- Engineered Wood Flooring — sqft — ₹250 — flooring
- Italian Marble Flooring — sqft — ₹400 — flooring
- Granite Flooring — sqft — ₹180 — flooring
- Anti-Skid Ceramic Tiles — sqft — ₹70 — flooring
- Epoxy Flooring (self-leveling) — sqft — ₹150 — flooring

**Ceiling (4 items):**
- Gypsum False Ceiling (plain) — sqft — ₹75 — ceiling
- Mineral Fiber Ceiling Tiles (600x600mm) — sqft — ₹65 — ceiling
- POP False Ceiling — sqft — ₹55 — ceiling
- Metal Grid Ceiling (exposed) — sqft — ₹95 — ceiling

**Door (4 items):**
- HDF Flush Door (35mm) — piece — ₹4500 — door
- Glass Swing Door (10mm tempered) — piece — ₹12000 — door
- Fire-Rated Door (30 min) — piece — ₹8500 — door
- Sliding Glass Door Panel — piece — ₹15000 — door

**Door Hardware (3 items):**
- Aluminum Door Frame — running_foot — ₹180 — door_hardware
- Stainless Steel Handle Set — piece — ₹650 — door_hardware
- Hydraulic Door Closer — piece — ₹1200 — door_hardware

**Paint (4 items):**
- Interior Acrylic Emulsion (per coat) — sqft — ₹12 — paint
- Wall Primer — sqft — ₹8 — paint
- Texture Paint (roller finish) — sqft — ₹25 — paint
- Anti-Fungal Paint — sqft — ₹18 — paint

**Electrical (5 items):**
- LED Light Point (with wiring) — piece — ₹850 — electrical
- Power Socket (5A) — piece — ₹350 — electrical
- Modular Switch Board (4-module) — piece — ₹450 — electrical
- Data/Network Point (CAT6) — piece — ₹1200 — electrical
- AC Point (with copper piping) — piece — ₹3500 — electrical

**Baseboard (2 items):**
- PVC Skirting (75mm) — running_foot — ₹25 — baseboard
- Wooden Skirting (75mm teak) — running_foot — ₹85 — baseboard

**Waterproofing (3 items):**
- Cementitious Waterproofing (2-coat) — sqft — ₹35 — waterproofing
- Liquid Membrane Waterproofing — sqft — ₹55 — waterproofing
- Waterproof Ceramic Wall Tiles — sqft — ₹65 — waterproofing

**Specialty (5 items):**
- Raised Access Flooring (steel pedestal) — sqft — ₹220 — specialty
- Kitchen Backsplash Tiles (ceramic) — sqft — ₹75 — specialty
- Acoustic Soundproofing Panel — sqft — ₹180 — specialty
- Anti-Static Vinyl Flooring — sqft — ₹160 — specialty
- Stainless Steel Backsplash — sqft — ₹250 — specialty

**Total: 45 items.**

Update the `seed_materials` function to delete existing materials first (clean re-seed for MVP), then insert all 45. Update the final summary print to show item count and category breakdown.

Also update the SETUP COMPLETE message at the end to reflect the new count.
  </action>
  <verify>
    <automated>python -c "from app.services.materials_repository import get_all_materials, get_materials_by_category; print('Repository imports OK')" && python -c "from scripts.setup_supabase_schema import DEFAULT_MATERIALS; cats = set(m['category'] for m in DEFAULT_MATERIALS); print(f'Materials: {len(DEFAULT_MATERIALS)} items across {len(cats)} categories: {sorted(cats)}')"</automated>
  </verify>
  <done>Materials seed contains ~45 items across at least 9 categories with realistic ₹ rates. materials_repository.py exposes get_all_materials() and get_materials_by_category(). All categories represented: wall, flooring, ceiling, door, door_hardware, paint, electrical, baseboard, waterproofing, specialty.</done>
</task>

</tasks>

<verification>
1. `python -c "from app.models.bom import BOMLineItem, BOMResult, MaterialInfo, MaterialCategory"` — all types import
2. `python -c "from app.models.database import MaterialPricing; assert hasattr(MaterialPricing, 'category')"` — category field exists
3. `python -c "from scripts.setup_supabase_schema import DEFAULT_MATERIALS; assert len(DEFAULT_MATERIALS) >= 40"` — sufficient materials
4. `python -c "from app.services.materials_repository import get_all_materials"` — repository importable
5. `pytest tests/ -x --timeout=60` — existing tests still pass (no regressions)
</verification>

<success_criteria>
- BOM domain types (BOMLineItem, BOMResult, MaterialInfo) are importable and instantiable
- MaterialPricing model has a category field
- Materials seed data contains ~45 items across 9+ categories with real ₹ rates
- materials_repository.py provides DB access for materials catalog
- All existing tests pass (no regressions from model changes)
</success_criteria>

<output>
After completion, create `.planning/phases/02-bom-calculator-engine/02-bom-calculator-engine-01-SUMMARY.md`
</output>
