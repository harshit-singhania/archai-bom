---
phase: 02-bom-calculator-engine
plan: 02
status: completed
completed_date: "2026-02-28"
files_created:
  - app/services/bom_calculator.py
  - tests/test_bom_calculator.py
tests_executed:
  - pytest tests/test_bom_calculator.py -v
---

# Plan 02 Summary

Implemented a deterministic, pure BOM calculator that converts layout geometry into priced BOM line items.

## Delivered

- Added `calculate_bom(layout, materials, ceiling_height_mm)` in `app/services/bom_calculator.py` with no DB calls and no side effects.
- Implemented geometry helpers for wall length, room perimeter, sqft/foot conversions, material selection, and line-item building.
- Implemented deterministic category rules:
  - wall quantity from wall length x ceiling height
  - flooring/ceiling from room area
  - baseboard from room perimeter
  - paint + primer from perimeter-derived wall surface area
  - electrical points from area heuristics
  - door panel + frame + handle + closer per door
  - room-type specialty logic (waterproofing, backsplash, raised flooring, lab specialty)
- Added `tests/test_bom_calculator.py` covering single-room geometry mapping, bathroom specialty behavior, empty layout, grand total integrity, and amount calculations.

## Verification Result

`pytest tests/test_bom_calculator.py -v` passed (6/6).
