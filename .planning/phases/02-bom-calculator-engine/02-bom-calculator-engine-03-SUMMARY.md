---
phase: 02-bom-calculator-engine
plan: 03
status: completed
completed_date: "2026-02-28"
files_created:
  - tests/test_bom_integration.py
files_modified:
  - app/services/job_runner.py
tests_executed:
  - python -c "from app.services.job_runner import _run_generate_job"
  - pytest tests/test_bom_integration.py -v
  - pytest tests/test_repositories.py tests/test_status_endpoint.py tests/test_async_jobs.py -q
---

# Plan 03 Summary

Wired deterministic BOM calculation into the async generate pipeline and added integration-level BOM behavior tests.

## Delivered

- Updated `_run_generate_job()` in `app/services/job_runner.py` to:
  - load pricing catalog via `get_all_materials()`
  - map rows into `MaterialInfo`
  - run `calculate_bom(layout, materials)`
  - persist non-zero `total_cost_inr` and `line_items`/room metadata into `bom_data`
- Added graceful fallback behavior: if materials load or BOM calculation fails, layout persistence still succeeds with `total_cost_inr = 0.0` and warning logs.
- Added `tests/test_bom_integration.py` with office/bathroom/empty-layout scenarios validating category coverage, geometry-driven quantities, totals, and door item generation.

## Verification Result

- `tests/test_bom_integration.py` passed (10/10).
- Regression checks for repositories/status/async jobs passed (57 tests).
