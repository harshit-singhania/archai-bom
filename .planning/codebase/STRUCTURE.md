# Codebase Structure

**Analysis Date:** 2026-02-27

## Directory Layout

```text
achai-bom/
├── app/                 # Flask app code (API, services, models, core config)
├── tests/               # Pytest suites (unit + integration)
├── sample_pdfs/         # Test fixture PDFs (raster and vector subsets)
├── scripts/             # Operational/setup helper scripts
├── postman/             # Manual API collection + local environment
├── Dockerfile           # Container build/runtime definition
└── requirements.txt     # Python dependency manifest
```

## Directory Purposes

**`app/`:**
- Purpose: Runtime application code
- Contains: HTTP entrypoint (`app/main.py`), routes (`app/api/routes.py`), business services (`app/services/*.py`), typed models (`app/models/*.py`), settings/clients (`app/core/*.py`)
- Key files: `app/main.py`, `app/api/routes.py`, `app/services/generation_pipeline.py`, `app/services/ingestion_pipeline.py`

**`tests/`:**
- Purpose: Verification for service logic and API behavior
- Contains: `test_*.py` files plus module-level helper payload builders/fixtures
- Key files: `tests/test_generation_endpoint.py`, `tests/test_generation_pipeline.py`, `tests/test_ingestion_pipeline.py`, `tests/test_constraint_checker.py`

**`sample_pdfs/`:**
- Purpose: Real-world style PDF fixtures used by integration-like tests
- Contains: `sample_pdfs/vector/test_floorplan.pdf` and many raster PDFs in `sample_pdfs/raster/*.pdf`
- Key files: `sample_pdfs/vector/test_floorplan.pdf`

**`scripts/`:**
- Purpose: One-off automation and validation helpers
- Contains: schema seeding (`scripts/setup_supabase_schema.py`), data conversion (`scripts/convert_images_to_pdf.py`), shell validators (`scripts/validate-all.sh`)
- Key files: `scripts/setup_supabase_schema.py`, `scripts/convert_images_to_pdf.py`

**`postman/`:**
- Purpose: Manual API smoke tests
- Contains: collection and env files
- Key files: `postman/phase2-generate.postman_collection.json`, `postman/local.postman_environment.json`

## Key File Locations

**Entry Points:**
- `app/main.py`: Flask app factory-ish bootstrap and blueprint wiring
- `scripts/setup_supabase_schema.py`: CLI schema setup + seed flow

**Configuration:**
- `app/core/config.py`: Environment-driven settings model
- `.env.example`: Required env variable template
- `Dockerfile`: Runtime/container configuration

**Core Logic:**
- `app/services/ingestion_pipeline.py`: Vector-first ingestion with raster fallback
- `app/services/layout_generator.py`: Gemini prompt/schema generation
- `app/services/generation_pipeline.py`: Retry + parallel candidate orchestration
- `app/services/constraint_checker.py`: Geometry constraint engine

**Testing:**
- `tests/test_generation_endpoint.py`: `/api/v1/generate` endpoint behavior
- `tests/test_ingestion_pipeline.py`: `/api/v1/ingest` integration-style coverage
- `tests/test_raster_wall_extractor.py`: Raster fallback service behavior

## Naming Conventions

**Files:**
- `snake_case.py` module naming: `generation_pipeline.py`, `test_generation_pipeline.py`

**Directories:**
- Lowercase package folders aligned to concern: `api`, `services`, `models`, `core`

## Where to Add New Code

**New Feature:**
- Primary code: route in `app/api/routes.py` and orchestration/service in `app/services/`
- Tests: add matching file in `tests/` using `test_<feature>.py`

**New Component/Module:**
- Implementation: domain contracts in `app/models/`, behavior in `app/services/`, infra wiring in `app/core/`

**Utilities:**
- Shared helpers: colocate with feature service module (private `_helper` functions) or create focused utility module under `app/services/` when reused

## Special Directories

**`sample_pdfs/`:**
- Purpose: Fixture corpus for extraction/ingestion tests
- Generated: mixed (checked-in fixtures plus generated content workflows)
- Committed: Yes

**`app/**/__pycache__/`:**
- Purpose: CPython bytecode cache
- Generated: Yes
- Committed: No (should remain ignored by `__pycache__` rule in `.gitignore`)

**`.planning/codebase/`:**
- Purpose: generated mapping docs for GSD planning/execution context
- Generated: Yes
- Committed: Yes (intended planning artifacts)

---

*Structure analysis: 2026-02-27*
