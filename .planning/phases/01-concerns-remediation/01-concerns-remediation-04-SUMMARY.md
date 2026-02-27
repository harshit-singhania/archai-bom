---
phase: 01-concerns-remediation
plan: 04
subsystem: tests
tags: [fragile-tests, fixture-refactor, pdf-discovery, conftest, FRAG-01]
dependency_graph:
  requires: []
  provides: [shared-pdf-fixtures, lazy-pdf-discovery]
  affects: [tests/test_ingestion_pipeline.py, tests/test_semantic_extractor.py, tests/test_wall_detector.py, tests/test_pdf_extractor.py]
tech_stack:
  added: []
  patterns: [pytest-conftest-fixtures, lazy-discovery, subdirectory-based-categorization]
key_files:
  created:
    - tests/conftest.py
  modified:
    - tests/test_ingestion_pipeline.py
    - tests/test_semantic_extractor.py
    - tests/test_wall_detector.py
    - tests/test_pdf_extractor.py
decisions:
  - Used subdirectory-based discovery (sample_pdfs/vector/, sample_pdfs/raster/) over root-level os.listdir + per-file categorization
  - Kept module-level lists for pytest.mark.parametrize compatibility; called helper at module load rather than at import
  - Unified categorize_pdf() definition in conftest; delegated from test modules via import
metrics:
  duration: 8m
  completed: 2026-02-27
---

# Phase 1 Plan 4: Lazy PDF Discovery Fixtures Summary

**One-liner:** Moved import-time os.listdir scanning into safe conftest helpers using subdirectory-based PDF discovery, eliminating FRAG-01 coupling across four test modules.

## Objective

Remove import-time filesystem coupling from integration-heavy test modules so test collection succeeds in any environment regardless of fixture directory state.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Introduce shared PDF discovery fixtures | 5b20bce | tests/conftest.py (created) |
| 2 | Refactor integration-heavy modules to use fixtures | c7ff946 | test_ingestion_pipeline.py, test_semantic_extractor.py, test_wall_detector.py, test_pdf_extractor.py |

## What Was Built

### Task 1: tests/conftest.py

Created shared fixture module with:

- `_list_pdfs_in(directory)` — safe list helper, returns `[]` when directory is absent
- `categorize_pdf(pdf_path)` — shared classifier returning "vector"/"raster"/"empty"/"error"; fitz imported lazily inside function
- `get_vector_pdf_paths()` — returns PDFs from `sample_pdfs/vector/`
- `get_raster_pdf_paths()` — returns PDFs from `sample_pdfs/raster/`
- `get_all_pdf_paths()` — union of vector + raster paths
- `get_categorized_pdf_paths()` — returns `(all, vector, raster)` tuple; falls back to root-level discovery + per-file categorization when subdirectories are absent
- Session-scoped fixtures: `vector_pdf_paths`, `raster_pdf_paths`, `all_pdf_paths`, `any_pdf_path`

### Task 2: Refactored Test Modules

All four modules changed from:
```python
# OLD: import-time filesystem scan (fragile)
ALL_PDF_PATHS = [
    os.path.join(SAMPLE_PDFS_DIR, f) for f in os.listdir(SAMPLE_PDFS_DIR)
    ...
]
VECTOR_PDF_PATHS = [p for p in ALL_PDF_PATHS if categorize_pdf(p) == "vector"]
```

To:
```python
# NEW: conftest helper (safe, guards against missing dirs)
from tests.conftest import get_categorized_pdf_paths
ALL_PDF_PATHS, VECTOR_PDF_PATHS, RASTER_PDF_PATHS = get_categorized_pdf_paths()
```

Additional changes:
- Removed duplicate `categorize_pdf()` definitions from all four modules
- `test_ingestion_pipeline.py`: updated hardcoded PDF path from `sample_pdfs/test_floorplan.pdf` to `sample_pdfs/vector/test_floorplan.pdf` (Rule 1 - Bug fix, path was wrong for new dir structure)
- `test_pdf_extractor.py`: local `categorize_pdf()` now delegates to conftest version

## Verification Results

```
2028 passed, 6 warnings in 94.60s (0:01:34)
```

Collection: 2028 tests collected in 4.30s with no import errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed hardcoded PDF path in test_api_ingest_endpoint**
- **Found during:** Task 2
- **Issue:** `test_api_ingest_endpoint` referenced `sample_pdfs/test_floorplan.pdf` (root) which does not exist; file is at `sample_pdfs/vector/test_floorplan.pdf`
- **Fix:** Updated path to `sample_pdfs/vector/test_floorplan.pdf`
- **Files modified:** tests/test_ingestion_pipeline.py
- **Commit:** c7ff946

## Success Criteria

FRAG-01 resolved:
- No `os.listdir()` at import time in any of the four target modules
- Test collection succeeds even with missing/empty sample_pdfs directories
- All 2028 tests pass

## Self-Check: PASSED

Files verified:
- tests/conftest.py: exists and contains get_categorized_pdf_paths()
- tests/test_ingestion_pipeline.py: imports from tests.conftest
- tests/test_semantic_extractor.py: imports from tests.conftest
- tests/test_wall_detector.py: imports from tests.conftest
- tests/test_pdf_extractor.py: imports from tests.conftest

Commits verified:
- 5b20bce: feat(01-04): introduce shared PDF discovery fixtures
- c7ff946: refactor(01-04): replace import-time os.listdir with conftest lazy helpers
