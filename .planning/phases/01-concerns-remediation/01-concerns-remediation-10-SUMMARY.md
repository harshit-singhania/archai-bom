---
phase: 01-concerns-remediation
plan: 10
subsystem: async-queue
tags: [async, queue, redis, rq, worker, jobs, non-blocking, scaling]
dependency_graph:
  requires:
    - 01-concerns-remediation-05  # floorplan_repository, bom_repository
    - 01-concerns-remediation-07  # persistence-integrated API routes
  provides:
    - AsyncJob model with full lifecycle (queued/running/succeeded/failed)
    - job_repository.py: CRUD helpers for async job records
    - job_runner.py: in-process job executor for ingest and generate pipelines
    - queue_worker.py: Redis/RQ entrypoint for background execution
    - Non-blocking /ingest and /generate endpoints (202 Accepted)
    - GET /jobs/<job_id> status polling endpoint
  affects:
    - app/api/routes.py: converted to enqueue model
    - app/models/database.py: new async_jobs table
tech_stack:
  added:
    - redis>=5.0.0 (queue backend)
    - rq>=1.16.0 (Redis Queue job framework with retry/backoff)
  patterns:
    - Async job lifecycle pattern (queued -> running -> succeeded | failed)
    - Enqueue-and-poll API pattern (202 + status_url)
    - Worker process separation (API process enqueues, worker executes)
    - Mock-based testing for queue/pipeline without live Redis or PDFs
key_files:
  created:
    - app/models/database.py (AsyncJob model added to existing file)
    - app/services/job_repository.py
    - app/services/job_runner.py
    - app/workers/__init__.py
    - app/workers/queue_worker.py
    - tests/test_async_jobs.py
  modified:
    - app/api/routes.py (enqueue model replacing synchronous execution)
    - app/core/config.py (REDIS_URL, JOB_QUEUE_NAME, retry settings)
    - requirements.in (redis, rq added)
decisions:
  - "Redis/RQ chosen over Celery for lower complexity footprint; rq is already compatible with existing redis package"
  - "run_job() is synchronous and testable without live Redis — queue only transports job_id"
  - "enqueue_ingest_job/enqueue_generate_job are named wrappers to support patch-based test isolation"
  - "Retry policy uses exponential backoff: [5, 10, 20] seconds for 3 retries (from settings)"
  - "API returns 202 even if Redis is temporarily unreachable (enqueue failure logged as warning for ingest)"
  - "status endpoint GET /status/<pdf_id> extended with jobs[] list (backward-compatible)"
  - "GET /jobs/<job_id> is a new dedicated async job polling endpoint"
metrics:
  duration: 5m
  completed_date: "2026-02-27"
  tasks_completed: 3
  tasks_planned: 3
  files_created: 6
  files_modified: 4
  tests_added: 28
  tests_total_passing: 37
---

# Phase 1 Plan 10: Async Queue Architecture Summary

**One-liner:** Redis/RQ async job queue with enqueue-and-poll API pattern, durable job lifecycle model, and background worker for non-blocking PDF ingest and layout generation.

## What Was Built

This plan moves all heavy workloads (PDF extraction, Gemini vision, layout generation) off synchronous request threads and into a Redis-backed job queue. The API now returns immediately with a `job_id` and `status_url`; a separate worker process executes the pipeline and persists the outcome.

### AsyncJob Model (`app/models/database.py`)

Added `AsyncJob` SQLModel table (`async_jobs`) with:
- `job_type` (`"ingest"` | `"generate"`)
- `status` (`queued` -> `running` -> `succeeded` | `failed`)
- `payload` (JSON string for cross-process portability)
- `floorplan_id` (nullable FK to floorplans)
- `result_ref` (JSON dict — result_type, result_id on success)
- `error_message` (text on failure)
- `created_at`, `updated_at`, `started_at`, `finished_at` timestamps

### Job Repository (`app/services/job_repository.py`)

Clean repository boundary with:
- `create_job(job_type, payload, floorplan_id) -> int`
- `get_job_by_id(job_id) -> Optional[dict]`
- `list_jobs_by_floorplan(floorplan_id) -> List[dict]`
- `mark_job_running(job_id) -> bool`
- `mark_job_succeeded(job_id, result_ref) -> bool`
- `mark_job_failed(job_id, error_message) -> bool`

All functions return typed dicts for clean service boundaries (no ORM objects exposed).

### Job Runner (`app/services/job_runner.py`)

Single `run_job(job_id)` entrypoint:
1. Loads job from DB, marks running
2. Deserialises payload JSON
3. Dispatches to `_run_ingest_job()` or `_run_generate_job()`
4. On success: calls `mark_job_succeeded` with result_ref
5. On any exception: calls `mark_job_failed` with error message (never re-raises)

Workers remain alive even on job failures. Ingest jobs update floorplan status in DB (processing -> processed | error). Generate jobs persist BOM snapshots when successful.

### Queue Worker (`app/workers/queue_worker.py`)

- `enqueue_ingest_job(db_job_id)` / `enqueue_generate_job(db_job_id)` — API-facing functions
- `start_worker()` — blocking RQ worker loop (run in separate process/container)
- Retry policy: exponential backoff [5, 10, 20]s, configurable via settings
- CLI entrypoint: `python -m app.workers.queue_worker`
- Graceful ImportError handling when `rq` is absent in test environments

### API Routes (`app/api/routes.py`)

Converted to non-blocking enqueue pattern:

| Endpoint | Before | After |
|----------|--------|-------|
| `POST /ingest` | Runs pipeline synchronously, returns wall data | Creates floorplan + job, enqueues, returns 202 + job_id |
| `POST /generate` | Runs generation synchronously, returns layout | Creates job, enqueues, returns 202 + job_id |
| `GET /status/<pdf_id>` | Returns floorplan lifecycle | Returns floorplan + jobs[] list (backward-compatible) |
| `GET /jobs/<job_id>` | (new) | Returns async job state, result_ref, error_message |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect wall schema in test**
- **Found during:** Task 3 test run
- **Issue:** Test used `{start: {x,y}, end: {x,y}}` wall format; `WallSegment` model requires `{x1, y1, x2, y2, length_pts, thickness}`
- **Fix:** Updated test payload to match actual `WallSegment` Pydantic schema; also added required `page_dimensions` field to `SpatialGraph`
- **Files modified:** `tests/test_async_jobs.py`
- **Commit:** e7dbbe0

### Out-of-Scope Pre-existing Issues

Discovered and logged (not fixed — pre-existing):
- `test_routes_prefix.py::test_routes_use_api_v1_prefix` connects to real PostgreSQL without test_db fixture isolation — fails in environments without live DB. Was failing before this plan.

## Test Coverage

| Test Class | Tests | What It Covers |
|-----------|-------|----------------|
| `TestJobRepositoryLifecycle` | 17 | Full CRUD lifecycle, all state transitions, serialisation fields |
| `TestWorkerExecutesAndPersistsResults` | 4 | Mock-based worker execution, success/failure persistence |
| `TestAPIEnqueueAndPoll` | 7 | 202 responses, job_id in response, validation 400s |
| `test_status_endpoint.py` | 9 | Pre-existing floorplan status (still passing) |
| **Total** | **37** | All passing |

## Self-Check: PASSED

Files created/exist:
- `app/services/job_repository.py` ✓
- `app/services/job_runner.py` ✓
- `app/workers/queue_worker.py` ✓
- `tests/test_async_jobs.py` ✓

Commits:
- `6c07f7c` — Task 1: async job model and repository ✓
- `56dc4cb` — Task 2: queue worker and job runner ✓
- `e7dbbe0` — Task 3: async API routes ✓
