---
status: complete
phase: 01-concerns-remediation
source: 01-concerns-remediation-01-SUMMARY.md, 01-concerns-remediation-02-SUMMARY.md, 01-concerns-remediation-03-SUMMARY.md, 01-concerns-remediation-04-SUMMARY.md, 01-concerns-remediation-05-SUMMARY.md, 01-concerns-remediation-06-SUMMARY.md, 01-concerns-remediation-07-SUMMARY.md, 01-concerns-remediation-08-SUMMARY.md, 01-concerns-remediation-09-SUMMARY.md, 01-concerns-remediation-10-SUMMARY.md
started: 2026-02-27T12:00:00Z
updated: 2026-02-27T12:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. No print() noise from semantic extractor
expected: Running tests/test_semantic_extractor.py with -s flag produces no raw print() output during the success path. Metrics like page dimensions go through logger.debug only.
result: pass

### 2. Supabase URL validation rejects bad values
expected: tests/test_setup_supabase_schema.py shows the script correctly rejects missing, empty, or malformed SUPABASE_PROJECT_URL values and fails with a clear error.
result: pass

### 3. API routes all served under /api/v1 prefix from config
expected: tests/test_routes_prefix.py passes. /ingest, /generate, and /status endpoints all resolve under /api/v1 — no hardcoded /v1 in route decorators.
result: pass

### 4. Lockfile exists and Docker install uses it
expected: requirements-lock.txt exists and pip install --dry-run -r requirements-lock.txt completes without errors.
result: pass

### 5. Test collection succeeds with empty fixture directories
expected: pytest --collect-only completes without ImportError or FileNotFoundError. 2028+ tests collected.
result: pass

### 6. API returns 401 for requests without API key in production mode
expected: With API_AUTH_KEY set and DEBUG=False, hitting /api/v1/ingest without X-API-Key returns HTTP 401. tests/test_security_controls.py shows 6 tests passing.
result: pass

### 7. Repository layer CRUD operations pass all tests
expected: pytest tests/test_repositories.py shows 20 tests passing for project, floorplan, and BOM operations.
result: pass

### 8. Ingest endpoint returns pdf_id and transitions lifecycle states
expected: POST /api/v1/ingest enqueues a job and returns 202 with job_id. GET /api/v1/status/<pdf_id> returns lifecycle status with timestamps. tests/test_status_endpoint.py shows 9 passing.
result: pass

### 9. Constraint checker handles 100 rooms within 5 seconds
expected: tests/test_constraint_checker_performance.py shows all 5 performance tests passing. Large layouts complete well under 5–10s time budgets.
result: pass

### 10. Gemini calls respect timeout and retry with backoff
expected: tests/test_layout_generator.py and tests/test_generation_pipeline.py show 22 tests passing covering timeout enforcement, transient error retry with exponential backoff, and adaptive candidate count adjustment.
result: pass

### 11. Heavy jobs are non-blocking — API returns 202 immediately
expected: POST /api/v1/ingest and POST /api/v1/generate return HTTP 202 with job_id immediately. tests/test_async_jobs.py shows 28 tests passing.
result: pass

### 12. Job status polling endpoint works
expected: GET /api/v1/jobs/<job_id> returns async job state, result_ref on success, error_message on failure.
result: pass

## Summary

total: 12
passed: 12
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
