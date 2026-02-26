---
phase: 3
plan: 3
wave: 2
---

# Plan 3.3: BOM Assembly, Pricing & XLSX Export

## Objective
Wire all calculators into a single BOM assembly service that takes a `GeneratedLayout` and produces a priced `BOMSummary`. Then implement Excel export to .xlsx format — the primary deliverable for estimators.

## Context
- `.gsd/SPEC.md` — "BOM export to .xlsx", "deterministic calculator"
- `.gsd/phases/3/RESEARCH.md` — Q4 (openpyxl)
- `app/models/bom.py` — `BOMLineItem`, `BOMSummary` (Plan 3.1)
- `app/services/bom_calculators.py` — 7 calculator functions (Plan 3.2)
- `app/data/material_catalog.py` — pricing catalog (Plan 3.1)
- `app/models/layout.py` — `GeneratedLayout` (input)

## Tasks

<task type="auto">
  <name>Create BOM assembly service</name>
  <files>app/services/bom_assembler.py</files>
  <action>
    Create the orchestration service that calls all calculators and assembles the final BOM:

    ```python
    def assemble_bom(
        layout: GeneratedLayout,
        ceiling_height_mm: float = 3048.0,
        overhead_pct: float = 10.0,
    ) -> BOMSummary:
    ```

    Implementation:
    1. Call each calculator with the appropriate layout fields:
       - `calculate_wall_quantities(layout.interior_walls, ceiling_height_mm)`
       - `calculate_door_quantities(layout.doors)`
       - `calculate_flooring_quantities(layout.rooms)`
       - `calculate_ceiling_quantities(layout.rooms)`
       - `calculate_paint_quantities(layout.interior_walls, layout.perimeter_walls, layout.doors, ceiling_height_mm)`
       - `calculate_electrical_quantities(layout.rooms)`
       - `calculate_skirting_quantities(layout.rooms)`
    2. Collect all `BOMLineItem` lists into one flat list
    3. Apply pricing from material catalog to each line item
    4. Calculate subtotal = sum of all line item totals
    5. Calculate total = subtotal × (1 + overhead_pct / 100)
    6. Return `BOMSummary` with all fields populated

    This function is DETERMINISTIC — same layout always produces same BOM. No randomness, no AI.
  </action>
  <verify>pytest tests/test_bom_assembler.py -v</verify>
  <done>assemble_bom() takes a GeneratedLayout and returns a complete BOMSummary with all categories populated; subtotal and total are correct</done>
</task>

<task type="auto">
  <name>Implement XLSX export and BOM API endpoint</name>
  <files>app/services/bom_exporter.py, app/api/routes.py</files>
  <action>
    **Part A: XLSX Exporter** (`app/services/bom_exporter.py`)

    ```python
    def export_bom_to_xlsx(bom: BOMSummary) -> bytes:
        """Export BOM to Excel bytes (in-memory, no temp files)."""
    ```

    Excel structure:
    - Sheet 1: "BOM Summary"
      - Header row: Project info, generated date, ceiling height, overhead %
      - Table headers: Category | Material | Unit | Qty | Rate (₹) | Total (₹) | Room | Notes
      - One row per BOMLineItem, grouped by category
      - Subtotal row at bottom
      - Overhead row
      - Grand total row (bold)
    - Format: Column widths auto-sized, number formatting for INR (₹ #,##0.00), header row bold

    Use `openpyxl` — add to requirements.txt if not present.

    **Part B: API Endpoint** (add to `app/api/routes.py`)

    ```python
    @api_bp.route("/v1/bom/generate", methods=["POST"])
    def generate_bom():
        """Generate BOM from a GeneratedLayout."""
    ```

    Request body (JSON):
    ```json
    {
      "layout": { ... GeneratedLayout ... },
      "ceiling_height_mm": 3048.0,
      "overhead_pct": 10.0
    }
    ```

    Response (JSON):
    ```json
    {
      "bom": { ... BOMSummary.model_dump() ... },
      "line_item_count": 42,
      "total_inr": 125000.00
    }
    ```

    Also add:
    ```python
    @api_bp.route("/v1/bom/export", methods=["POST"])
    def export_bom():
        """Generate BOM and return as .xlsx download."""
    ```
    - Same request body as /v1/bom/generate
    - Returns .xlsx file with `Content-Disposition: attachment; filename=bom_export.xlsx`
    - Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  </action>
  <verify>pytest tests/test_bom_exporter.py tests/test_bom_endpoint.py -v</verify>
  <done>XLSX export produces valid Excel file with correct formatting; both API endpoints return correct responses; xlsx download works</done>
</task>

<task type="auto">
  <name>Write tests for assembly and export</name>
  <files>tests/test_bom_assembler.py, tests/test_bom_exporter.py, tests/test_bom_endpoint.py</files>
  <action>
    **test_bom_assembler.py:**
    - Test with a minimal GeneratedLayout (1 room, 2 walls, 1 door)
    - Verify all 7 categories have line items
    - Verify subtotal = sum of line item totals
    - Verify total includes overhead
    - Verify determinism: same input → same output

    **test_bom_exporter.py:**
    - Test export_bom_to_xlsx returns bytes
    - Test bytes are valid xlsx (load with openpyxl, check sheet name)
    - Test row count matches line_item_count + header + summary rows
    - Test grand total cell value matches BOMSummary.total_inr

    **test_bom_endpoint.py:**
    - POST /v1/bom/generate with valid layout → 200, correct JSON
    - POST /v1/bom/generate with empty layout → 400
    - POST /v1/bom/export with valid layout → 200, content-type xlsx
    - POST /v1/bom/export with invalid layout → 400

    Create a shared fixture: `sample_generated_layout()` returning a minimal but valid GeneratedLayout for testing.
  </action>
  <verify>pytest tests/test_bom_assembler.py tests/test_bom_exporter.py tests/test_bom_endpoint.py -v --tb=short</verify>
  <done>All assembly, export, and endpoint tests pass; XLSX output is valid; API returns correct status codes</done>
</task>

## Success Criteria
- [ ] `assemble_bom()` produces complete BOMSummary from GeneratedLayout
- [ ] BOM is deterministic — same layout always produces same output
- [ ] XLSX export produces valid Excel file openable in Excel/Google Sheets
- [ ] POST /v1/bom/generate returns JSON BOM
- [ ] POST /v1/bom/export returns downloadable .xlsx
- [ ] All tests pass