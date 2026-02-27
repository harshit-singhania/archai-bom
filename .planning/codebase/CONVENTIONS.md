# Coding Conventions

**Analysis Date:** 2026-02-27

## Naming Patterns

**Files:**
- Use `snake_case.py` for modules and `test_<module>.py` for tests (`app/services/layout_generator.py`, `tests/test_layout_generator.py`)

**Functions:**
- Use `snake_case` for public functions (`generate_validated_layout`, `extract_vectors`) and prefix internal helpers with `_` (`_build_prompt`, `_constraint_score`)

**Variables:**
- Use descriptive `snake_case`; reserve uppercase for constants (`_RASTER_SCALE` in `app/services/raster_wall_extractor.py`)

**Types:**
- Use PascalCase Pydantic/SQLModel classes (`GeneratedLayout`, `ConstraintResult`, `Project`)

## Code Style

**Formatting:**
- Tool used: Not detected (no `pyproject.toml`, `setup.cfg`, or formatter config at root)
- Key settings: Follow existing style in `app/` and `tests/` (4-space indent, type hints, double-quoted strings)

**Linting:**
- Tool used: Not detected (no Ruff/Flake8 config files found)
- Key rules: Apply pragmatic consistency with current modules (docstrings + explicit typing on service/model APIs)

## Import Organization

**Order:**
1. Python stdlib imports (`os`, `tempfile`, `json`, `math`)
2. Third-party imports (`flask`, `pydantic`, `fitz`, `google.genai`, `shapely`)
3. Local app imports (`from app...`)

**Path Aliases:**
- Use absolute package paths from `app` (example: `from app.services.ingestion_pipeline import ingest_pdf` in `app/api/routes.py`)

## Error Handling

**Patterns:**
- Validate request/model inputs early and return structured errors at API boundary (`app/api/routes.py`)
- Raise `ValueError`/`RuntimeError` from service layer for invalid state/external failures (`app/services/layout_generator.py`, `app/services/raster_wall_extractor.py`)
- Return empty model fallbacks for optional semantic extraction (`app/services/semantic_extractor.py`)

## Logging

**Framework:** `logging` + occasional `print`

**Patterns:**
- Initialize module logger with `logging.getLogger(__name__)` in service modules
- Prefer logger calls in runtime services (`app/services/ingestion_pipeline.py`, `app/services/semantic_extractor.py`)
- Keep direct `print` mostly in scripts/tests; avoid adding new runtime prints in `app/services/`

## Comments

**When to Comment:**
- Use module/function docstrings for intent and units; keep inline comments for non-obvious geometry/LLM prompt behavior (`app/services/constraint_checker.py`, `app/services/layout_generator.py`)

**JSDoc/TSDoc:**
- Not applicable (Python codebase)
- Python docstrings are used consistently across modules

## Function Design

**Size:**
- Keep reusable helper functions small and focused (`_parse_color`, `_rect_to_lines`, `_format_constraint_feedback`)
- Accept larger orchestrators for pipelines where step sequencing matters (`validate_layout`, `generate_validated_layout`)

**Parameters:**
- Prefer typed signatures with defaults for behavior tuning (`page_num=0`, `grid_mm=50`, `parallel_candidates=1`)

**Return Values:**
- Return typed models rather than ad-hoc dicts in services (`WallDetectionResult`, `GeneratedLayout`, `ConstraintResult`)
- Convert to JSON only at API boundary (`model_dump`, `to_json` in `app/api/routes.py`)

## Module Design

**Exports:**
- Import concrete functions/classes directly from modules; avoid wildcard imports

**Barrel Files:**
- Not used; `__init__.py` files are empty in `app/` packages

---

*Convention analysis: 2026-02-27*
