# Codebase Concerns

**Analysis Date:** 2026-02-27

## Tech Debt

**Supabase persistence path is defined but not integrated into API flows:**
- Issue: Database models and client helpers exist but request pipelines do not persist or query data.
- Files: `app/models/database.py`, `app/core/supabase.py`, `app/api/routes.py`, `scripts/setup_supabase_schema.py`
- Impact: Runtime behavior is effectively stateless and cannot leverage seeded schema for project/BOM lifecycle.
- Fix approach: Introduce persistence service modules (for example `app/services/project_repository.py`) and wire ingest/generate endpoints to store/retrieve records.

**Configuration drift around API prefix:**
- Issue: `API_V1_PREFIX` is defined but route registration uses hardcoded path fragments.
- Files: `app/core/config.py`, `app/main.py`, `app/api/routes.py`
- Impact: Route prefix changes require edits in multiple files and increase mismatch risk.
- Fix approach: Centralize prefix usage by deriving blueprint/route composition from `settings.API_V1_PREFIX`.

## Known Bugs

**Semantic extractor emits debug output in runtime service path:**
- Symptoms: Every semantic extraction prints page dimensions to stdout.
- Files: `app/services/semantic_extractor.py:46`
- Trigger: Any call to `extract_semantics(...)` when PDF page is opened.
- Workaround: Replace `print(...)` with structured logger call or remove debug line.

**Supabase URL builder fails unclearly when project URL is blank:**
- Symptoms: Database URL can be constructed with an empty project ref, causing downstream connection errors.
- Files: `scripts/setup_supabase_schema.py:46`, `scripts/setup_supabase_schema.py:52`
- Trigger: Running `scripts/setup_supabase_schema.py` with missing/invalid `SUPABASE_PROJECT_URL`.
- Workaround: Add explicit non-empty URL validation before formatting connection string.

## Security Considerations

**Public API surface without request authentication:**
- Risk: Unauthenticated callers can invoke compute-expensive generation endpoints.
- Files: `app/api/routes.py`, `app/main.py`
- Current mitigation: None detected in route handlers.
- Recommendations: Add auth middleware (API key/JWT), request quota/rate limiting, and payload size limits.

**Permissive CORS + default secret fallback:**
- Risk: Wide browser origin access and predictable secret fallback increase abuse risk in misconfigured deployments.
- Files: `app/main.py:10`, `app/main.py:13`
- Current mitigation: `SECRET_KEY` can be set through env.
- Recommendations: Restrict CORS origins and fail startup when `SECRET_KEY` is absent in production mode.

## Performance Bottlenecks

**Constraint validation uses pairwise geometric checks:**
- Problem: Room and fixture overlap checks scale quadratically with element count.
- Files: `app/services/constraint_checker.py`
- Cause: Nested loops over rooms and fixtures (`for i in range(len(...))` patterns) and expensive polygon intersections.
- Improvement path: Add spatial indexing (R-tree via Shapely STRtree) and early bounding-box prefilters.

**Parallel candidate generation can amplify external API cost/latency:**
- Problem: Multiple candidate calls per iteration multiply LLM requests and completion time variance.
- Files: `app/services/generation_pipeline.py`, `app/services/layout_generator.py`
- Cause: ThreadPool fan-out without explicit timeout/backoff budgeting per provider limits.
- Improvement path: Add per-call timeout/retry policy, adaptive candidate count, and provider quota-aware throttling.

## Fragile Areas

**Large integration-heavy test modules with import-time filesystem scanning:**
- Files: `tests/test_ingestion_pipeline.py`, `tests/test_semantic_extractor.py`, `tests/test_wall_detector.py`, `tests/test_pdf_extractor.py`
- Why fragile: Module import performs `os.listdir(...)` and PDF categorization, coupling test discovery to fixture directory state.
- Safe modification: Isolate scanning into fixtures or setup helpers and guard missing directories explicitly.
- Test coverage: High quantity of tests, but reliability depends on local fixture presence and environment assumptions.

## Scaling Limits

**Single-process synchronous request model for heavy AI/PDF workloads:**
- Current capacity: Gunicorn configured with 2 workers in `Dockerfile:28`; each request may run expensive PDF + Gemini + geometry steps.
- Limit: Throughput drops under concurrent generation/ingestion load; long-running requests tie up workers.
- Scaling path: Move heavy pipelines to async job queue (Celery/RQ), store job state, and keep API endpoints lightweight.

## Dependencies at Risk

**Unpinned transitive dependency resolution:**
- Risk: `requirements.txt` uses lower-bounded specifiers (`>=`) without lockfile.
- Impact: Reproducibility drift across environments and potential surprise breakages.
- Migration plan: Generate pinned lock set (`requirements-lock.txt`/Poetry/pip-tools) and use deterministic install in CI/CD.

## Missing Critical Features

**No durable job/result tracking for ingestion and generation:**
- Problem: `/api/pdf/status/<pdf_id>` currently returns a placeholder payload.
- Blocks: Reliable async processing UX and resumable workflow tracking.

**No authorization layer for production-facing endpoints:**
- Problem: API endpoints in `app/api/routes.py` do not enforce caller identity.
- Blocks: Safe public exposure and tenant isolation for commercial usage.

## Test Coverage Gaps

**Infrastructure and persistence modules are largely untested:**
- What's not tested: Supabase client lifecycle and SQLModel schema setup integration.
- Files: `app/core/supabase.py`, `app/models/database.py`, `scripts/setup_supabase_schema.py`
- Risk: Runtime/data-layer failures remain undiscovered until deployment-time usage.
- Priority: High

**Route-level coverage is uneven outside generation/ingestion happy paths:**
- What's not tested: `GET /api/pdf/status/<pdf_id>` remains placeholder and has no behavior-depth assertions.
- Files: `app/api/routes.py`, `tests/test_generation_endpoint.py`, `tests/test_ingestion_pipeline.py`
- Risk: Endpoint contract drift or incomplete implementation can ship unnoticed.
- Priority: Medium

---

*Concerns audit: 2026-02-27*
