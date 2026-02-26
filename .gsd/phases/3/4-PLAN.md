---
phase: 3
plan: 4
wave: 2
---

# Plan 3.4: Async Job Queue Infrastructure (Celery + Redis)

## Objective
Add Celery + Redis job queue infrastructure so that long-running operations (PDF ingestion, layout generation, BOM assembly) run as background tasks instead of blocking the HTTP request. Clients receive a job ID and poll for status.

## Context
- `.gsd/phases/3/RESEARCH.md` — Q1 (Celery + Redis selected)
- `app/api/routes.py` — Current synchronous endpoints
- `app/services/ingestion_pipeline.py` — `ingest_pdf()` (can take 5-30s for raster)
- `app/services/generation_pipeline.py` — `generate_validated_layout()` (can take 30-90s with retries)
- `app/services/bom_assembler.py` — `assemble_bom()` (fast, <1s, but depends on layout)
- `app/core/config.py` — Settings

## Tasks

<task type="auto">
  <name>Set up Celery + Redis infrastructure</name>
  <files>app/core/celery_app.py, app/core/config.py, requirements.txt</files>
  <action>
    **1. Add dependencies to requirements.txt:**
    - `celery>=5.3.0`
    - `redis>=5.0.0`

    **2. Add Redis settings to config.py:**
    ```python
    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = ""  # defaults to REDIS_URL
    CELERY_RESULT_BACKEND: str = ""  # defaults to REDIS_URL
    ```
    If CELERY_BROKER_URL is empty, fall back to REDIS_URL. Same for result backend.

    **3. Create Celery app factory** (`app/core/celery_app.py`):
    ```python
    from celery import Celery
    from app.core.config import settings

    def make_celery() -> Celery:
        broker = settings.CELERY_BROKER_URL or settings.REDIS_URL
        backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL
        celery = Celery(
            "achai_bom",
            broker=broker,
            backend=backend,
        )
        celery.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            task_track_started=True,
            result_expires=3600,  # 1 hour
            task_acks_late=True,
            worker_prefetch_multiplier=1,
        )
        return celery

    celery_app = make_celery()
    ```

    **4. Register task modules** in the Celery app config:
    ```python
    celery.conf.update(include=["app.tasks.pipeline_tasks"])
    ```
  </action>
  <verify>python -c "from app.core.celery_app import celery_app; print(f'Celery app: {celery_app.main}, broker: {celery_app.conf.broker_url}')"</verify>
  <done>Celery app importable, configured with Redis broker/backend, task serialization set to JSON</done>
</task>

<task type="auto">
  <name>Create async task wrappers and job status API</name>
  <files>app/tasks/__init__.py, app/tasks/pipeline_tasks.py, app/api/routes.py, app/models/jobs.py</files>
  <action>
    **1. Create job response model** (`app/models/jobs.py`):
    ```python
    class JobStatus(BaseModel):
        job_id: str
        status: str  # "pending", "started", "success", "failure"
        result: Optional[dict] = None
        error: Optional[str] = None
        created_at: datetime
    ```

    **2. Create Celery tasks** (`app/tasks/pipeline_tasks.py`):

    ```python
    @celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
    def ingest_pdf_task(self, pdf_path: str) -> dict:
        """Async wrapper for ingest_pdf(). Returns WallDetectionResult as dict."""
        result = ingest_pdf(pdf_path)
        return result.model_dump()

    @celery_app.task(bind=True, max_retries=1, default_retry_delay=10)
    def generate_layout_task(self, spatial_graph_dict: dict, prompt: str,
                             parallel_candidates: int = 2, max_workers: int = 4) -> dict:
        """Async wrapper for generate_validated_layout(). Returns GenerationResult as dict."""
        spatial_graph = SpatialGraph.model_validate(spatial_graph_dict)
        result = generate_validated_layout(spatial_graph, prompt, ...)
        return { ... serialized GenerationResult ... }

    @celery_app.task(bind=True)
    def generate_bom_task(self, layout_dict: dict, ceiling_height_mm: float = 3048.0,
                          overhead_pct: float = 10.0) -> dict:
        """Async wrapper for assemble_bom(). Returns BOMSummary as dict."""
        layout = GeneratedLayout.model_validate(layout_dict)
        bom = assemble_bom(layout, ceiling_height_mm, overhead_pct)
        return bom.model_dump(mode="json")
    ```

    Each task catches exceptions and records them via Celery's built-in failure tracking.

    **3. Add async API endpoints** (add to `app/api/routes.py`):

    ```python
    @api_bp.route("/v1/async/ingest", methods=["POST"])
    def async_ingest():
        """Submit PDF for async ingestion. Returns job_id."""
        # Save uploaded file to persistent temp location (not deleted immediately)
        # Submit ingest_pdf_task.delay(tmp_path)
        # Return {"job_id": task.id, "status": "pending"}, 202

    @api_bp.route("/v1/async/generate", methods=["POST"])
    def async_generate():
        """Submit layout generation job. Returns job_id."""
        # Parse spatial_graph + prompt from JSON body
        # Submit generate_layout_task.delay(...)
        # Return {"job_id": task.id, "status": "pending"}, 202

    @api_bp.route("/v1/async/bom", methods=["POST"])
    def async_bom():
        """Submit BOM generation job. Returns job_id."""
        # Parse layout from JSON body
        # Submit generate_bom_task.delay(...)
        # Return {"job_id": task.id, "status": "pending"}, 202

    @api_bp.route("/v1/jobs/<job_id>", methods=["GET"])
    def get_job_status(job_id: str):
        """Poll job status by ID."""
        # Use AsyncResult(job_id, app=celery_app)
        # Map Celery states: PENDING→pending, STARTED→started, SUCCESS→success, FAILURE→failure
        # Return JobStatus with result or error
    ```

    **Important:**
    - Keep existing synchronous endpoints unchanged — async endpoints are ADDITIVE
    - For async ingest, the temp file must persist until the worker processes it (use a dedicated temp dir, worker cleans up after)
    - Return HTTP 202 (Accepted) for all async submissions
    - The /v1/jobs/<job_id> endpoint is the universal status poller
  </action>
  <verify>pytest tests/test_async_endpoints.py -v</verify>
  <done>All 3 async endpoints return 202 with job_id; job status endpoint returns correct states; existing sync endpoints still work unchanged</done>
</task>

<task type="auto">
  <name>Write tests for async infrastructure</name>
  <files>tests/test_async_endpoints.py</files>
  <action>
    Write tests that mock Celery task submission (do NOT require running Redis/workers):

    1. **Async ingest endpoint:**
       - POST /v1/async/ingest with PDF → 202, response has job_id
       - POST /v1/async/ingest without file → 400
       - Mock `ingest_pdf_task.delay()` to verify it's called with correct path

    2. **Async generate endpoint:**
       - POST /v1/async/generate with valid JSON → 202
       - POST /v1/async/generate with missing prompt → 400
       - Mock `generate_layout_task.delay()` to verify args

    3. **Async BOM endpoint:**
       - POST /v1/async/bom with valid layout → 202
       - POST /v1/async/bom with invalid layout → 400

    4. **Job status endpoint:**
       - Mock `AsyncResult` with different states (PENDING, STARTED, SUCCESS, FAILURE)
       - Verify each maps to correct JobStatus response
       - SUCCESS → includes result dict
       - FAILURE → includes error message

    5. **Existing sync endpoints still work:**
       - POST /v1/ingest still returns 200 synchronously (not broken)
       - GET /health still returns 200

    Use `unittest.mock.patch` on Celery task `.delay()` methods. Do NOT require a running Redis instance.
  </action>
  <verify>pytest tests/test_async_endpoints.py -v --tb=short</verify>
  <done>All async endpoint tests pass without Redis; existing sync endpoints unaffected; job status returns correct state mappings</done>
</task>

## Success Criteria
- [ ] Celery app configured with Redis broker/backend
- [ ] 3 Celery tasks wrap existing pipeline functions
- [ ] 3 async endpoints return 202 with job_id
- [ ] Job status endpoint correctly maps Celery states
- [ ] Existing synchronous endpoints unchanged
- [ ] All tests pass without requiring running Redis/workers
- [ ] `celery -A app.core.celery_app worker --loglevel=info` starts without errors (manual verification)