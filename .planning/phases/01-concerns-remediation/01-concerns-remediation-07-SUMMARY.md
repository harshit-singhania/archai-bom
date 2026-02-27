---
phase: 01-concerns-remediation
plan: 07
subsystem: api
tags: [flask, sqlmodel, sqlite, persistence, status-endpoint, bom, floorplan]

# Dependency graph
requires:
  - phase: 01-concerns-remediation-02
    provides: Repository layer (floorplan_repository, bom_repository, project_repository)
  - phase: 01-concerns-remediation-06
    provides: Persistence layer with 24 passing tests

provides:
  - "Persistence-aware ingest route with lifecycle status transitions (uploaded->processing->processed/error)"
  - "pdf_id in ingest response for downstream status polling"
  - "Generate route with optional floorplan_id linkage and BOM snapshot persistence"
  - "Real status endpoint returning persisted state, timestamps, error context, generation summary"
  - "9 contract tests for status endpoint covering all lifecycle states"

affects:
  - status-endpoint-consumers
  - ingest-downstream-polling
  - generation-bom-tracking

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Non-blocking persistence: DB failures logged as warnings, pipeline continues"
    - "Nullable FK: project_id optional on Floorplan for standalone ingest"
    - "Lifecycle status transitions: uploaded->processing->processed/error with error_message field"
    - "Status response always includes stable schema fields regardless of record state"

key-files:
  created:
    - tests/test_status_endpoint.py
  modified:
    - app/api/routes.py
    - app/models/database.py
    - app/services/floorplan_repository.py
    - app/services/bom_repository.py

key-decisions:
  - "Non-blocking persistence: DB create/update failures are logged as warnings, not request failures"
  - "project_id made nullable (Optional[int]) on Floorplan to support standalone ingest without project context"
  - "Status endpoint uses int path param (/status/<int:pdf_id>) for type-safe routing"
  - "Generation BOM stored with total_cost_inr=0.0 as cost calculation is downstream; snapshot stored for provenance"
  - "created_at/updated_at added to Floorplan; created_at added to GeneratedBOM for lifecycle visibility"

patterns-established:
  - "Persistence wrapper pattern: route creates DB record -> marks processing -> runs service -> updates result"
  - "Status response schema: always includes pdf_id, status, created_at, updated_at, error_message, generation_summary"

requirements-completed: [TD-01, FEAT-01, TEST-02]

# Metrics
duration: 9min
completed: 2026-02-27
---

# Phase 1 Plan 7: Persistence-Integrated API Routes Summary

**Ingest/generate/status routes wired to SQLModel persistence with lifecycle status tracking (uploaded->processing->processed/error) and 9 contract tests for the status endpoint.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-27T11:11:56Z
- **Completed:** 2026-02-27T11:20:56Z
- **Tasks:** 3
- **Files modified:** 5 (4 modified, 1 created)

## Accomplishments

- Ingest route creates a durable `Floorplan` record, transitions through lifecycle states, persists extraction metadata, and returns `pdf_id` for polling
- Generate route accepts optional `floorplan_id` to persist `GeneratedBOM` snapshots linked to floorplans
- Status endpoint (`GET /status/<pdf_id>`) replaced placeholder with real persistence-backed implementation returning 404 for unknown IDs and stable JSON for all lifecycle states
- 9 contract tests covering all status values, 404 contract, generation_summary presence/absence, and required schema fields

## Task Commits

Each task was committed atomically:

1. **Task 1: Persist ingest lifecycle state** - `345f137` (feat)
2. **Task 2: Persist generation outputs linked to floorplan** - `fc98583` (feat)
3. **Task 3: Replace placeholder status endpoint with persisted status API** - `1ab3fa8` (feat)

## Files Created/Modified

- `app/api/routes.py` - Persistence-aware ingest/generate/status route orchestration
- `app/models/database.py` - Floorplan.project_id nullable; added error_message, created_at, updated_at to Floorplan; added created_at to GeneratedBOM
- `app/services/floorplan_repository.py` - Added update_floorplan_error(), made project_id optional, updated dict returns with timestamps
- `app/services/bom_repository.py` - Added created_at to all dict returns
- `tests/test_status_endpoint.py` - 9 contract tests for status endpoint lifecycle states and schema stability

## Decisions Made

- **Non-blocking persistence**: DB failures during ingest/generate are logged as warnings and never propagate to the caller — the pipeline result is always returned.
- **Nullable project_id**: Made `Floorplan.project_id` optional so the ingest endpoint works standalone without requiring a pre-existing project record.
- **Status endpoint type-safe routing**: Used `<int:pdf_id>` in Flask route pattern so invalid IDs return 404 automatically.
- **BOM total_cost_inr=0.0**: Generation snapshots store the layout/constraint result for provenance; actual cost calculation is a downstream concern.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added error_message and timestamp fields to Floorplan model**
- **Found during:** Task 1 (Persist ingest lifecycle state)
- **Issue:** Plan specified failure state with "error context" but the Floorplan model lacked an error_message field and timestamps needed for the status endpoint response
- **Fix:** Added `error_message: Optional[str]`, `created_at: datetime`, `updated_at: datetime` to Floorplan; added `created_at: datetime` to GeneratedBOM; added `update_floorplan_error()` repository function
- **Files modified:** app/models/database.py, app/services/floorplan_repository.py, app/services/bom_repository.py
- **Verification:** All 36 tests pass including 9 new status contract tests
- **Committed in:** 345f137 (Task 1 commit)

**2. [Rule 2 - Missing Critical] Made Floorplan.project_id nullable**
- **Found during:** Task 1 (Persist ingest lifecycle state)
- **Issue:** Existing Floorplan model had project_id as required non-nullable FK; ingest endpoint has no project context, so all DB creates would fail
- **Fix:** Changed `project_id: int` to `project_id: Optional[int] = Field(default=None, ..., nullable=True)` and updated create_floorplan() signature to make project_id an optional keyword argument
- **Files modified:** app/models/database.py, app/services/floorplan_repository.py
- **Verification:** Repository tests all pass (20/20); ingest tests pass
- **Committed in:** 345f137 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 2 - missing critical)
**Impact on plan:** Both fixes were essential for the plan's stated requirements (durable records, failure context). No scope creep.

## Issues Encountered

None - all changes executed cleanly without blocking issues.

## User Setup Required

None - no external service configuration required. Tests use in-memory SQLite isolation.

## Next Phase Readiness

- TD-01 (durable processing tracking) and FEAT-01 (generation result linking) are now implemented end-to-end
- TEST-02 (status endpoint contract coverage) is satisfied with 9 dedicated tests
- Status endpoint is ready for client polling integration
- BOM persistence supports downstream cost calculation phases

---
*Phase: 01-concerns-remediation*
*Completed: 2026-02-27*
