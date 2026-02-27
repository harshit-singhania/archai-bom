---
phase: 01-concerns-remediation
plan: 10
type: execute
wave: 4
depends_on:
  - 01-concerns-remediation-05
  - 01-concerns-remediation-07
files_modified:
  - app/core/config.py
  - app/models/database.py
  - app/services/job_repository.py
  - app/services/job_runner.py
  - app/workers/queue_worker.py
  - app/api/routes.py
  - tests/test_async_jobs.py
  - tests/test_status_endpoint.py
autonomous: true
requirements:
  - SCALE-01
  - FEAT-01
user_setup:
  - service: redis
    why: "Queue backend for async ingest/generation jobs"
    env_vars:
      - name: REDIS_URL
        source: "Local/hosted Redis connection string"
    dashboard_config:
      - task: "Provision Redis instance reachable by API and worker"
        location: "Infrastructure provider dashboard or local Docker runtime"
must_haves:
  truths:
    - "Ingest and generate requests return quickly with job identifiers instead of blocking full processing"
    - "Background worker executes heavy processing and updates durable job status"
    - "Status endpoint reports queued/running/succeeded/failed job state with result references"
  artifacts:
    - path: app/models/database.py
      provides: "Job tracking model/schema for async processing"
    - path: app/workers/queue_worker.py
      provides: "Background queue worker entrypoint"
    - path: app/api/routes.py
      provides: "Enqueue-based non-blocking API behavior"
  key_links:
    - from: app/api/routes.py
      to: app/services/job_repository.py
      via: "job creation and enqueue metadata"
      pattern: "queued|running|succeeded|failed"
    - from: app/workers/queue_worker.py
      to: app/services/job_runner.py
      via: "job execution and persistence updates"
      pattern: "run_job"
---

<objective>
Move heavy PDF and generation workloads off synchronous request threads.

Purpose: Resolve scaling limits from long-running compute in Flask request lifecycle.
Output: Async queue architecture, worker process, durable job states, and async API behavior.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@app/api/routes.py
@app/models/database.py
@app/services/ingestion_pipeline.py
@app/services/generation_pipeline.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add durable async job model and repository contracts</name>
  <files>app/models/database.py, app/services/job_repository.py</files>
  <action>Add a job tracking table/model (type, payload_ref, status, error_message, timestamps, result references) and repository helpers for lifecycle transitions. Ensure schema supports both ingest and generation job types and links to floorplan/BOM records.</action>
  <verify>
    <automated>pytest tests/test_async_jobs.py::test_job_repository_lifecycle -q</automated>
  </verify>
  <done>Jobs can be created, updated, and queried durably across process boundaries.</done>
</task>

<task type="auto">
  <name>Task 2: Implement queue worker and job runner</name>
  <files>app/core/config.py, app/services/job_runner.py, app/workers/queue_worker.py, tests/test_async_jobs.py</files>
  <action>Implement queue integration (Redis-backed), worker entrypoint, and job runner handlers that execute existing ingestion/generation pipelines and persist success/failure outcomes. Include retry/backoff policy for transient worker failures.</action>
  <verify>
    <automated>pytest tests/test_async_jobs.py::test_worker_executes_and_persists_results -q</automated>
  </verify>
  <done>Background worker can execute queued jobs and write final states/results to persistence.</done>
</task>

<task type="auto">
  <name>Task 3: Convert API routes to enqueue and poll model</name>
  <files>app/api/routes.py, tests/test_status_endpoint.py, tests/test_async_jobs.py</files>
  <action>Refactor ingest/generate endpoints to enqueue jobs and return 202 with job_id + status URL. Update status endpoint to return job state and resolved output references when complete. Keep backward-compatible response fields where feasible and document transition in tests.</action>
  <verify>
    <automated>pytest tests/test_status_endpoint.py tests/test_async_jobs.py -q</automated>
  </verify>
  <done>API is non-blocking for heavy operations and status endpoint reflects live async execution state.</done>
</task>

</tasks>

<verification>
Run async job and status suites; validate worker-driven state transitions end-to-end.
</verification>

<success_criteria>
SCALE-01 is resolved: heavy workloads no longer block request workers, and FEAT-01 durable tracking is complete in async mode.
</success_criteria>

<output>
After completion, create `.planning/phases/01-concerns-remediation/01-concerns-remediation-10-SUMMARY.md`
</output>
