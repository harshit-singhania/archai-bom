---
phase: 3
plan: 5
wave: 3
---

# Plan 3.5: End-to-End Pipeline Wiring & Integration Tests

## Objective
Wire the complete async pipeline: PDF upload → ingestion → generation → BOM → XLSX download, all flowing through Celery. Add chained task support so a single upload triggers the full pipeline automatically. Verify with integration tests.

## Context
- `app/tasks/pipeline_tasks.py` — Individual async tasks (Plan 3.4)
- `app/api/routes.py` — Async + sync endpoints (Plan 3.4)
- `app/services/bom_assembler.py` — BOM assembly (Plan 3.3)
- `app/services/generation_pipeline.py` — Layout generation
- `app/services/ingestion_pipeline.py` — PDF ingestion

## Tasks

<task type="auto">
  <name>Create chained pipeline task and full-pipeline endpoint</name>
  <files>app/tasks/pipeline_tasks.py, app/api/routes.py</files>
  <action>
    **1. Add a chained pipeline task** (`app/tasks/pipeline_tasks.py`):

    ```python
    @celery_app.task(bind=True)
    def full_pipeline_task(self, pdf_path: str, prompt: str,
                           ceiling_height_mm: float = 3048.0,
                           overhead_pct: float = 10.0) -> dict:
        """
        Full end-to-end pipeline: ingest → generate → BOM.
        Reports progress at each stage via self.update_state().
        """
    ```

    Implementation:
    1. `self.update_state(state="PROGRESS", meta={"stage": "ingesting"})` → call `ingest_pdf(pdf_path)`
    2. Build `SpatialGraph` from `WallDetectionResult` (walls, page dimensions)
    3. `self.update_state(state="PROGRESS", meta={"stage": "generating"})` → call `generate_validated_layout(spatial_graph, prompt)`
    4. If generation failed → return `{"success": false, "stage": "generation", "error": ...}`
    5. `self.update_state(state="PROGRESS", meta={"stage": "calculating_bom"})` → call `assemble_bom(layout, ceiling_height_mm, overhead_pct)`
    6. Return complete result: `{"success": true, "walls": ..., "layout": ..., "bom": ..., "xlsx_available": true}`
    7. Clean up temp PDF file

    **2. Add full pipeline endpoint** (`app/api/routes.py`):

    ```python
    @api_bp.route("/v1/async/pipeline", methods=["POST"])
    def async_full_pipeline():
        """Upload PDF + prompt → get back job_id for full pipeline."""
    ```

    Request: multipart form with `file` (PDF) + `prompt` (text) + optional `ceiling_height_mm`, `overhead_pct`
    Response: `{"job_id": "...", "status": "pending"}`, 202

    **3. Update job status endpoint** to include stage info:
    When Celery state is "PROGRESS", return the `meta.stage` field so clients can show progress like "Ingesting PDF..." → "Generating layout..." → "Calculating BOM..."

    **4. Add XLSX download endpoint for completed jobs:**

    ```python
    @api_bp.route("/v1/jobs/<job_id>/download", methods=["GET"])
    def download_job_result(job_id: str):
        """Download XLSX export for a completed pipeline job."""
    ```
    - Check job status is SUCCESS
    - Extract BOM from result
    - Call `export_bom_to_xlsx()` → return as file download
    - If job not complete → 404
  </action>
  <verify>pytest tests/test_full_pipeline.py -v</verify>
  <done>Full pipeline task chains all 3 stages; endpoint accepts PDF + prompt; job status shows progress stages; XLSX download works for completed jobs</done>
</task>

<task type="auto">
  <name>Write integration tests for full pipeline</name>
  <files>tests/test_full_pipeline.py</files>
  <action>
    Write integration tests (all Celery tasks mocked, no Redis required):

    1. **Full pipeline endpoint:**
       - POST /v1/async/pipeline with PDF + prompt → 202 with job_id
       - POST /v1/async/pipeline without file → 400
       - POST /v1/async/pipeline without prompt → 400

    2. **Job status with progress stages:**
       - Mock AsyncResult with state="PROGRESS", meta={"stage": "generating"}
       - Verify response includes stage field

    3. **XLSX download:**
       - Mock completed job with BOM result
       - GET /v1/jobs/{id}/download → 200 with xlsx content-type
       - GET /v1/jobs/{id}/download for pending job → 404

    4. **Error propagation:**
       - Mock pipeline failure at generation stage
       - Verify error message includes which stage failed

    5. **Existing endpoints regression:**
       - Verify all sync endpoints from Phase 1 and 2 still work
       - POST /v1/ingest (sync) → still returns 200

    Use pytest fixtures with a `sample_pdf_path` pointing to `sample_pdfs/test_floorplan.pdf`.
  </action>
  <verify>pytest tests/test_full_pipeline.py -v --tb=short</verify>
  <done>All pipeline integration tests pass; progress stages work; XLSX download works; no regressions on existing endpoints</done>
</task>

## Success Criteria
- [ ] Full pipeline task chains ingest → generate → BOM in a single job
- [ ] Progress reporting shows current stage via Celery update_state
- [ ] POST /v1/async/pipeline accepts PDF + prompt, returns job_id
- [ ] GET /v1/jobs/{id}/download returns XLSX for completed jobs
- [ ] All integration tests pass without Redis
- [ ] Existing synchronous endpoints remain unchanged
- [ ] `pytest` (full suite) passes with no regressions