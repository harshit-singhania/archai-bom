---
phase: 3
plan: 1
wave: 1
---

# Plan 3.1: BOM Schema & India-Market Material Catalog

## Objective
Define the Pydantic models for BOM line items and create a hardcoded India-market material catalog with CPWD-based pricing. This is the data foundation — all downstream calculators and exporters depend on these schemas.

## Context
- `.gsd/SPEC.md` — "No AI in math layer", "India-market pricing"
- `.gsd/phases/3/RESEARCH.md` — Q2 (categories), Q3 (pricing), Q5 (ceiling height)
- `app/models/layout.py` — GeneratedLayout schema (input to BOM)
- `app/models/database.py` — Existing MaterialPricing SQLModel

## Tasks

<task type="auto">
  <name>Create BOM line item models</name>
  <files>app/models/bom.py</files>
  <action>
    Create Pydantic models for BOM output:

    1. `BOMLineItem` — single material line:
       - `category: str` — e.g., "drywall", "flooring", "ceiling", "paint", "doors", "electrical", "skirting", "glass_partition"
       - `material_name: str` — e.g., "Gypsum Board 12.5mm"
       - `unit: str` — "sqft", "rft", "piece", "point"
       - `quantity: float` — calculated from geometry
       - `rate_inr: float` — unit price in INR
       - `total_inr: float` — quantity × rate
       - `room_name: Optional[str]` — which room this belongs to (None for shared items)
       - `notes: str = ""` — calculation notes

    2. `BOMSummary` — complete BOM output:
       - `line_items: List[BOMLineItem]`
       - `subtotal_inr: float` — sum of all line item totals
       - `overhead_pct: float = 10.0` — contractor overhead percentage
       - `total_inr: float` — subtotal × (1 + overhead_pct/100)
       - `ceiling_height_mm: float = 3048.0` — assumed ceiling height (10ft default)
       - `generated_at: datetime`
       - `layout_prompt: str` — the original prompt used for generation

    3. `MaterialCatalogEntry` — single material in the catalog:
       - `material_name: str`
       - `category: str`
       - `unit: str`
       - `default_rate_inr: float`
       - `room_types: List[str]` — which room types use this material (e.g., ["office", "conference"] for carpet tiles)

    Do NOT duplicate the existing `MaterialPricing` SQLModel in database.py — these are separate concerns (BOM output vs. database storage). The catalog entries are used at calculation time; the database model is for persistence.
  </action>
  <verify>python -c "from app.models.bom import BOMLineItem, BOMSummary, MaterialCatalogEntry; print('Models OK')"</verify>
  <done>All three models importable, all fields have correct types and defaults</done>
</task>

<task type="auto">
  <name>Create hardcoded India-market material catalog</name>
  <files>app/data/material_catalog.py</files>
  <action>
    Create a module containing the default material catalog as a Python list of `MaterialCatalogEntry` objects. Include these materials (rates from RESEARCH.md Q3):

    **Drywall/Partition:**
    - Gypsum Board 12.5mm — ₹55/sqft — all room types
    - Metal Stud Frame (GI) — ₹30/sqft — all room types
    - Glass Partition 12mm — ₹450/sqft — ["office", "conference", "reception"]

    **Flooring:**
    - Vitrified Tiles 600x600 — ₹75/sqft — ["office", "corridor", "reception", "lobby"]
    - Carpet Tiles (standard) — ₹110/sqft — ["office", "conference", "boardroom"]
    - Vinyl Flooring — ₹65/sqft — ["clinic", "operatory", "lab", "hospital"]
    - Ceramic Tiles — ₹55/sqft — ["bathroom", "kitchen", "pantry", "utility"]

    **Ceiling:**
    - Grid False Ceiling 2x2 — ₹70/sqft — ["office", "corridor", "conference"]
    - Gypsum False Ceiling — ₹85/sqft — ["reception", "lobby", "boardroom"]

    **Paint:**
    - Interior Emulsion Paint — ₹12/sqft — all room types

    **Doors:**
    - Flush Door (solid core) — ₹5500/piece — all room types
    - Glass Door (frameless) — ₹12000/piece — ["reception", "conference", "boardroom"]

    **Electrical:**
    - Electrical Point (5A) — ₹850/point — all room types

    **Trim:**
    - PVC Skirting — ₹45/rft — all room types

    Also create a helper function:
    ```python
    def get_material_for_room(category: str, room_type: str) -> MaterialCatalogEntry:
        """Return the best matching material for a category and room type."""
    ```
    This should match room_type against the `room_types` list, falling back to the first material in that category if no specific match.

    Create the `app/data/` directory with an `__init__.py`.
  </action>
  <verify>python -c "from app.data.material_catalog import DEFAULT_CATALOG, get_material_for_room; print(f'{len(DEFAULT_CATALOG)} materials loaded'); m = get_material_for_room('flooring', 'office'); print(f'Office flooring: {m.material_name} @ ₹{m.default_rate_inr}/{m.unit}')"</verify>
  <done>Catalog has 14+ materials, get_material_for_room returns correct material for known room types and falls back gracefully for unknown types</done>
</task>

## Success Criteria
- [ ] `BOMLineItem`, `BOMSummary`, `MaterialCatalogEntry` models pass validation with sample data
- [ ] Material catalog contains 14+ entries covering all categories
- [ ] `get_material_for_room()` returns correct material for known room types
- [ ] `get_material_for_room()` falls back gracefully for unknown room types
- [ ] `pytest tests/test_bom_models.py` passes (write basic model validation tests)