# Architecture

**Analysis Date:** 2026-02-27

## Pattern Overview

**Overall:** Layered Flask service with pipeline-oriented domain services

**Key Characteristics:**
- Keep HTTP concerns in `app/api/routes.py` and route to service functions in `app/services/*.py`
- Represent payloads and domain entities with Pydantic/SQLModel classes in `app/models/*.py`
- Compose generation/ingestion as deterministic step pipelines (`extract -> transform -> validate`) in `app/services/ingestion_pipeline.py` and `app/services/generation_pipeline.py`

## Layers

**Application Entry Layer:**
- Purpose: Create Flask app, middleware, and health/root endpoints
- Location: `app/main.py`
- Contains: `Flask(...)`, `CORS(app)`, blueprint registration
- Depends on: `app.api.routes`, `app.core.config`
- Used by: Gunicorn (`app.main:app`) and local `python app/main.py`

**API Layer:**
- Purpose: Validate requests, orchestrate service calls, map exceptions to HTTP responses
- Location: `app/api/routes.py`
- Contains: `/v1/ingest`, `/v1/generate`, `/pdf/status/<id>` handlers
- Depends on: `app.models.spatial`, `app.services.ingestion_pipeline`, `app.services.generation_pipeline`
- Used by: Flask app via blueprint mount in `app/main.py:16`

**Service Layer:**
- Purpose: Implement business logic for PDF ingestion, generation, snapping, and validation
- Location: `app/services/*.py`
- Contains: extraction (`pdf_extractor.py`), wall detection (`wall_detector.py`), raster fallback (`raster_wall_extractor.py`), generation (`layout_generator.py`, `generation_pipeline.py`), constraints (`constraint_checker.py`), snapping (`grid_snapper.py`)
- Depends on: `app.models.*`, third-party libs (`fitz`, `google.genai`, `shapely`)
- Used by: API layer and tests

**Domain Model Layer:**
- Purpose: Define typed contracts for geometry, layout DSL, constraints, and persistence schema
- Location: `app/models/*.py`
- Contains: Pydantic models (`geometry.py`, `spatial.py`, `layout.py`, `constraints.py`, `generation.py`, `semantic.py`) and SQLModel tables (`database.py`)
- Depends on: Pydantic/SQLModel
- Used by: API and services for request/response and internal contracts

**Core Infrastructure Layer:**
- Purpose: Environment settings and external client setup
- Location: `app/core/config.py`, `app/core/supabase.py`
- Contains: `Settings(BaseSettings)`, lazy Supabase client singleton
- Depends on: env vars and Supabase SDK
- Used by: `app/main.py` and service modules requiring settings

## Data Flow

**PDF Ingestion Flow:**

1. Upload received in `app/api/routes.py:16` and persisted to temporary file.
2. `ingest_pdf(...)` in `app/services/ingestion_pipeline.py` runs vector extraction via `extract_vectors(...)`.
3. If vectors exist, `detect_walls(...)` returns `WallDetectionResult`; if empty, flow falls back to Gemini raster extraction in `extract_walls_from_raster(...)`.

**Layout Generation Flow:**

1. JSON body validated and converted to `SpatialGraph` in `app/api/routes.py:91`.
2. `generate_validated_layout(...)` in `app/services/generation_pipeline.py` runs candidate generation (`generate_layout`), grid snapping (`snap_layout_to_grid`), and constraint validation (`validate_layout`).
3. Loop retries with feedback prompt until pass/fail; endpoint responds with `200` on success or `422` with latest constraint summary.

**State Management:**
- Request handling is stateless; all pipeline state is local to function scope.
- Optional process-level singleton exists for Supabase client in `app/core/supabase.py` (`_supabase_client`), currently not consumed by API routes.

## Key Abstractions

**SpatialGraph:**
- Purpose: Canonical floorplan representation entering generation
- Examples: `app/models/spatial.py`, request parsing in `app/api/routes.py:92`
- Pattern: Strict Pydantic model boundary between transport JSON and service logic

**GeneratedLayout:**
- Purpose: Output DSL for rooms/walls/doors/fixtures
- Examples: `app/models/layout.py`, serialization in `app/api/routes.py:119`
- Pattern: Schema-first generation + validation (`model_json_schema()`, `model_validate(...)`)

**ConstraintResult:**
- Purpose: Structured validation signal for retry loop and API response
- Examples: `app/models/constraints.py`, validation in `app/services/constraint_checker.py`
- Pattern: Separate errors vs warnings to drive retry decisioning

## Entry Points

**Flask App Entry:**
- Location: `app/main.py`
- Triggers: Gunicorn startup or direct module execution
- Responsibilities: App creation, CORS, blueprint registration, `/` and `/health`

**API Blueprint Entry:**
- Location: `app/api/routes.py`
- Triggers: HTTP requests to `/api/v1/ingest`, `/api/v1/generate`, `/api/pdf/status/<pdf_id>`
- Responsibilities: Input checks, model validation, pipeline invocation, HTTP status mapping

**Schema Setup Script Entry:**
- Location: `scripts/setup_supabase_schema.py`
- Triggers: Manual CLI invocation
- Responsibilities: Create SQLModel tables and seed sample project/material/BOM records

## Error Handling

**Strategy:** Raise typed service exceptions and translate to JSON HTTP responses at route boundary

**Patterns:**
- Validate inputs early and return `400` in `app/api/routes.py`
- Raise `RuntimeError`/`ValueError` in services (`app/services/layout_generator.py`, `app/services/raster_wall_extractor.py`)
- Catch broad exceptions in route handlers and return `500` with message in `app/api/routes.py`

## Cross-Cutting Concerns

**Logging:** Python logging with module loggers in ingestion/raster/semantic services; partial direct prints remain in `app/services/semantic_extractor.py`
**Validation:** Pydantic model validation at IO boundaries plus geometric validation in `app/services/constraint_checker.py`
**Authentication:** Not implemented on API routes (`app/api/routes.py` has no auth guard)

---

*Architecture analysis: 2026-02-27*
