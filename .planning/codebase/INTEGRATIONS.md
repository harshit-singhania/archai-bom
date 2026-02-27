# External Integrations

**Analysis Date:** 2026-02-27

## APIs & External Services

**Generative AI / Vision:**
- Google Gemini - layout generation and raster/semantic extraction
  - SDK/Client: `google-generativeai` via `from google import genai` in `app/services/layout_generator.py`, `app/services/raster_wall_extractor.py`, and `app/services/semantic_extractor.py`
  - Auth: `GOOGLE_API_KEY` from `app/core/config.py` and `.env.example`

**Backend Platform:**
- Supabase - configured client and Postgres connection helpers
  - SDK/Client: `supabase` in `app/core/supabase.py`
  - Auth: `SUPABASE_PROJECT_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_PASSWORD` from `app/core/config.py` and `.env.example`

## Data Storage

**Databases:**
- PostgreSQL (Supabase-hosted target)
  - Connection: derived URL in `scripts/setup_supabase_schema.py:get_database_url`
  - Client: SQLModel/SQLAlchemy in `app/models/database.py` and `scripts/setup_supabase_schema.py`

**File Storage:**
- Local filesystem for uploads and sample corpora (`tempfile` in `app/api/routes.py`, fixtures in `sample_pdfs/`)
- Supabase Storage URL exists in seeded sample data in `scripts/setup_supabase_schema.py:108`

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- Custom / not implemented for API consumers
  - Implementation: no request auth checks in `app/api/routes.py`; endpoints are publicly callable within network scope

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry/Rollbar client wiring in `app/`)

**Logs:**
- Python stdlib logging in service modules (`logging.getLogger(__name__)`) in `app/services/ingestion_pipeline.py`, `app/services/raster_wall_extractor.py`, and `app/services/semantic_extractor.py`
- Direct `print(...)` output in `app/services/semantic_extractor.py:46` and multiple test/script files

## CI/CD & Deployment

**Hosting:**
- Containerized Flask/Gunicorn deployment pattern in `Dockerfile`

**CI Pipeline:**
- Not detected (no `.github/workflows/`, GitLab CI files, or other pipeline config present)

## Environment Configuration

**Required env vars:**
- `PROJECT_NAME`, `DEBUG`, `SECRET_KEY` (settings in `app/core/config.py`)
- `GOOGLE_API_KEY` (Gemini calls in `app/services/layout_generator.py`, `app/services/raster_wall_extractor.py`, `app/services/semantic_extractor.py`)
- `SUPABASE_PROJECT_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_PASSWORD` (Supabase config in `app/core/config.py` and `app/core/supabase.py`)
- `GENERATION_PARALLEL_CANDIDATES`, `GENERATION_MAX_WORKERS` (generation concurrency in `app/core/config.py` and `app/api/routes.py`)

**Secrets location:**
- `.env` file present at repo root (do not commit secret values)
- `.env.example` provides placeholder keys only

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

---

*Integration audit: 2026-02-27*
