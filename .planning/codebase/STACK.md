# Technology Stack

**Analysis Date:** 2026-02-27

## Languages

**Primary:**
- Python 3.11 - API server, domain models, pipelines, and tests in `app/` and `tests/`

**Secondary:**
- Bash - operational scripts in `scripts/*.sh`
- JSON - API tooling and environment definitions in `postman/*.json`

## Runtime

**Environment:**
- CPython 3.11 (containerized) in `Dockerfile:1`

**Package Manager:**
- pip (requirements-based workflow) in `Dockerfile:18` and `requirements.txt`
- Lockfile: missing

## Frameworks

**Core:**
- Flask >=3.0.0 - HTTP app and routing in `app/main.py` and `app/api/routes.py`
- Pydantic v2 + pydantic-settings - schema validation and env config in `app/models/*.py` and `app/core/config.py`
- SQLModel >=0.0.16 - relational models for Supabase Postgres in `app/models/database.py`

**Testing:**
- pytest >=8.0.0 - test runner for all suites in `tests/`
- pytest-flask >=1.3.0 - Flask test client patterns in `tests/test_generation_endpoint.py` and `tests/test_ingestion_pipeline.py`

**Build/Dev:**
- Gunicorn >=21.2.0 - production WSGI server in `Dockerfile:28`
- Docker (python:3.11-slim base) - reproducible runtime in `Dockerfile`

## Key Dependencies

**Critical:**
- `google-generativeai` >=0.3.0 - Gemini calls for layout and raster/semantic extraction in `app/services/layout_generator.py`, `app/services/raster_wall_extractor.py`, and `app/services/semantic_extractor.py`
- `pymupdf` >=1.23.0 - vector extraction and PDF rasterization in `app/services/pdf_extractor.py`, `app/services/raster_wall_extractor.py`, and `app/services/semantic_extractor.py`
- `shapely` >=2.0.0 - geometric constraint validation in `app/services/constraint_checker.py`

**Infrastructure:**
- `supabase` >=2.3.0 - Supabase client wiring in `app/core/supabase.py`
- `sqlmodel` >=0.0.16 + SQLAlchemy JSON type - Postgres schema definitions in `app/models/database.py`
- `flask-cors` >=4.0.0 - CORS middleware in `app/main.py:13`

## Configuration

**Environment:**
- Settings are centralized in `app/core/config.py` via `BaseSettings` with `.env` loading (`Config.env_file = ".env"`)
- Reference env template is `.env.example` (contains required keys for Gemini and Supabase integration)
- Ignore local secrets with `.gitignore:4` (`.env`)

**Build:**
- Container build and runtime config in `Dockerfile`
- Dependency manifest in `requirements.txt`
- No `pyproject.toml`, `setup.cfg`, `tox.ini`, or lint config detected at repo root

## Platform Requirements

**Development:**
- Python 3.11 environment compatible with `requirements.txt`
- System deps for compiled wheels inside container (`build-essential`) in `Dockerfile:12`
- Local sample data directories used by tests: `sample_pdfs/raster/` and `sample_pdfs/vector/`

**Production:**
- WSGI deployment target using Gunicorn serving `app.main:app` on port 5000 in `Dockerfile:24` and `Dockerfile:28`

---

*Stack analysis: 2026-02-27*
