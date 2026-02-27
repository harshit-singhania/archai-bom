---
phase: 01-concerns-remediation
plan: 07
type: execute
wave: 3
depends_on:
  - 01-concerns-remediation-02
  - 01-concerns-remediation-06
files_modified:
  - app/api/routes.py
  - app/models/database.py
  - app/services/ingestion_pipeline.py
  - app/services/project_repository.py
  - app/services/floorplan_repository.py
  - app/services/bom_repository.py
  - tests/test_ingestion_pipeline.py
  - tests/test_generation_endpoint.py
  - tests/test_status_endpoint.py
autonomous: true
requirements:
  - TD-01
  - FEAT-01
  - TEST-02
must_haves:
  truths:
    - "Ingest requests create and update durable floorplan records with lifecycle status"
    - "Generate requests persist result snapshots linked to floorplans"
    - "Status endpoint returns real persisted state instead of placeholder payload"
  artifacts:
    - path: app/api/routes.py
      provides: "Persistence-aware ingest/generate/status route orchestration"
    - path: app/models/database.py
      provides: "Fields needed for durable processing and status details"
    - path: tests/test_status_endpoint.py
      provides: "Dedicated status contract tests"
  key_links:
    - from: app/api/routes.py
      to: app/services/floorplan_repository.py
      via: "create/update floorplan status transitions"
      pattern: "uploaded|processing|processed|error"
    - from: app/api/routes.py
      to: app/services/bom_repository.py
      via: "persist generation outputs"
      pattern: "GeneratedBOM|bom_data"
---

<objective>
Integrate persistence into API flows and implement durable status tracking.

Purpose: Eliminate stateless processing and ship a real status endpoint for ingest/generation lifecycle visibility.
Output: Route-level persistence wiring, status model behavior, and contract tests.
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
@tests/test_generation_endpoint.py
@tests/test_ingestion_pipeline.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Persist ingest lifecycle state</name>
  <files>app/api/routes.py, app/services/floorplan_repository.py, tests/test_ingestion_pipeline.py</files>
  <action>Update ingest route to create a floorplan record, mark processing state transitions, persist extraction metadata/results, and store failure state with error context. Include `pdf_id` in ingest response for downstream polling.</action>
  <verify>
    <automated>pytest tests/test_ingestion_pipeline.py::test_api_ingest_endpoint -q</automated>
  </verify>
  <done>Ingest route returns persistent IDs and floorplan status transitions are durable.</done>
</task>

<task type="auto">
  <name>Task 2: Persist generation outputs linked to floorplan</name>
  <files>app/api/routes.py, app/services/bom_repository.py, tests/test_generation_endpoint.py</files>
  <action>Require or accept floorplan linkage in generation payload, persist generation result snapshots (iterations, constraint summary, layout JSON), and store GeneratedBOM rows tied to floorplan records. Preserve existing response contract fields.</action>
  <verify>
    <automated>pytest tests/test_generation_endpoint.py -q</automated>
  </verify>
  <done>Successful generation requests produce persisted BOM/result records tied to floorplans.</done>
</task>

<task type="auto">
  <name>Task 3: Replace placeholder status endpoint with persisted status API</name>
  <files>app/api/routes.py, tests/test_status_endpoint.py</files>
  <action>Implement GET status route to return durable status details (`uploaded|processing|processed|error`), timestamps, and optional generation summary for the requested id. Return 404 for unknown ids and stable error JSON schema.</action>
  <verify>
    <automated>pytest tests/test_status_endpoint.py -q</automated>
  </verify>
  <done>Status endpoint reflects persisted reality and no longer returns placeholder data.</done>
</task>

</tasks>

<verification>
Run ingest, generate, and status test modules against persistence-backed routes.
</verification>

<success_criteria>
TD-01 and FEAT-01 are implemented end-to-end, and TEST-02 route-level status coverage exists.
</success_criteria>

<output>
After completion, create `.planning/phases/01-concerns-remediation/01-concerns-remediation-07-SUMMARY.md`
</output>
