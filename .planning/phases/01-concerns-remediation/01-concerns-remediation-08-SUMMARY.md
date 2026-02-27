---
phase: 01-concerns-remediation
plan: 08
subsystem: constraint-checker
tags: [performance, spatial-index, strtree, geometry, regression-tests]
dependency_graph:
  requires: []
  provides: [indexed-constraint-validation, performance-regression-coverage]
  affects: [app/services/constraint_checker.py, tests/test_constraint_checker_performance.py]
tech_stack:
  added: []
  patterns: [STRtree spatial index, bbox prefilter before polygon intersection]
key_files:
  created:
    - tests/test_constraint_checker_performance.py
  modified:
    - app/services/constraint_checker.py
decisions:
  - "Use Shapely STRtree (already a project dependency) for O(n log n) candidate prefiltering instead of adding a separate R-tree library"
  - "Keep fixture STRtree scoped per-room to avoid cross-room false candidates"
  - "Performance envelope set at 5s for 100 rooms / 400 fixtures and 10s for 500 combined — conservative to tolerate CI variance"
metrics:
  duration: 2m
  completed: 2026-02-27
  tasks_completed: 2
  files_changed: 2
---

# Phase 1 Plan 08: STRtree-Indexed Constraint Checker Summary

STRtree spatial indexing applied to constraint_checker room and fixture overlap loops, eliminating O(n^2) polygon intersection cost and guarded by a performance regression test harness.

## What Was Built

### Task 1: STRtree-Backed Candidate Filtering (commit: 4c19578)

Refactored two O(n^2) full-pairwise intersection loops in `validate_layout`:

**Room-room overlap loop (was O(n^2)):**
- Replaced nested `for i / for j` loop with `STRtree.query(poly_a)` bounding-box prefilter
- Only runs `poly_a.intersection(poly_b)` on geometrically adjacent candidates returned by the tree
- Violation semantics, tolerance threshold (10,000 mm^2), and error type unchanged

**Fixture-fixture overlap loop (was O(n^2) per room):**
- Built a per-room `STRtree` over fixture polygons
- Prefilters candidates by bbox before calling `.intersection().area`
- Scoped to each room's fixtures to avoid spurious cross-room candidates

**Behavioral equivalence:** All 8 existing `test_constraint_checker.py` tests pass unchanged.

### Task 2: Performance Regression Test Harness (commit: 9584a42)

Created `tests/test_constraint_checker_performance.py` with:

| Test | Scale | Envelope |
|------|-------|----------|
| `test_large_room_layout_completes_within_time_budget` | 100 rooms | 5s |
| `test_large_fixture_layout_completes_within_time_budget` | 400 fixtures (20x20) | 5s |
| `test_combined_high_entity_layout_completes_within_time_budget` | 500 entities (50x10) | 10s |
| `test_single_room_is_instant` | 1 room | 1s |
| `test_correctness_preserved_at_scale` | 20 rooms + injected overlap | overlap detected |

Actual observed runtime: all 5 tests in **0.55s** (vs 5-10s envelopes), demonstrating the index efficiency.

## Verification Results

```
tests/test_constraint_checker.py              8 passed
tests/test_constraint_checker_performance.py  5 passed
Total: 13 passed in 0.72s
```

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **STRtree over separate R-tree library:** Shapely 2.x ships STRtree natively. No new dependency needed.
2. **Per-room fixture index:** Scoping the STRtree per room avoids false candidates between rooms and keeps index construction O(k) where k is fixtures-per-room.
3. **Conservative timing envelopes:** 5-10s limits leave headroom for slow CI environments while still catching O(n^2) regressions (which would take minutes at these scales).

## Self-Check: PASSED

- FOUND: app/services/constraint_checker.py
- FOUND: tests/test_constraint_checker_performance.py
- FOUND: .planning/phases/01-concerns-remediation/01-concerns-remediation-08-SUMMARY.md
- FOUND: commit 4c19578 (Task 1)
- FOUND: commit 9584a42 (Task 2)
