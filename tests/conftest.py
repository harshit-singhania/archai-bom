"""
Shared test configuration and fixtures.

Provides:
- Shared ``test_db`` fixture backed by real Supabase/PostgreSQL.
  Tests that write to the DB must request this fixture; it truncates
  all application tables after each test so tests are fully isolated
  without spinning up a separate database engine.
- Lazy PDF discovery helpers and fixtures that are safe when
  sample_pdfs/ directories are missing or empty. No filesystem scanning
  occurs at import time — all discovery is deferred to fixture execution
  or explicit helper calls.
"""

from __future__ import annotations

import os
import pytest
from sqlalchemy import text
from sqlmodel import SQLModel

import app.models.database  # noqa: F401 — registers all SQLModel tables
from app.core import database as db_module


# ---------------------------------------------------------------------------
# Shared Supabase test_db fixture
# ---------------------------------------------------------------------------

# Tables in safe TRUNCATE order (children before parents to respect FKs).
_TRUNCATE_ORDER = [
    "async_jobs",
    "generated_boms",
    "floorplans",
    "projects",
]


@pytest.fixture
def test_db():
    """Supabase-backed test fixture — truncates application tables after each test.

    Ensures the real Supabase schema exists (idempotent) and cleans up
    rows written during the test so tests don't interfere with each other.
    Use this fixture in any test that reads from or writes to the database.
    """
    engine = db_module.get_engine()

    # Ensure schema is up-to-date (no-op when tables already exist).
    SQLModel.metadata.create_all(engine)

    # Reset the session maker so it binds fresh at the start of each test.
    db_module._session_maker = None

    yield engine

    # Reset session maker so no stale session leaks into the next test.
    db_module._session_maker = None

    # Truncate in FK-safe order after each test.
    with engine.begin() as conn:
        for table in _TRUNCATE_ORDER:
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))


# ---------------------------------------------------------------------------
# Directory helpers (safe — do not scan at import time)
# ---------------------------------------------------------------------------

_SAMPLE_PDFS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "sample_pdfs")
)
_VECTOR_SUBDIR = os.path.join(_SAMPLE_PDFS_DIR, "vector")
_RASTER_SUBDIR = os.path.join(_SAMPLE_PDFS_DIR, "raster")


def _list_pdfs_in(directory: str) -> list[str]:
    """Return sorted absolute PDF paths under *directory*, or [] if absent."""
    if not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith(".pdf") and os.path.isfile(os.path.join(directory, f))
    )


def _list_pdfs_flat(directory: str) -> list[str]:
    """
    Return sorted absolute PDF paths directly under *directory* (non-recursive),
    falling back to [] when the directory is missing.
    """
    if not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith(".pdf") and os.path.isfile(os.path.join(directory, f))
    )


# ---------------------------------------------------------------------------
# Shared PDF categorization helper
# ---------------------------------------------------------------------------


def categorize_pdf(pdf_path: str) -> str:
    """
    Classify a PDF as 'vector', 'raster', 'empty', or 'error'.

    Uses PyMuPDF's page.get_drawings() heuristic: any drawing means vector.
    Falls back gracefully on open/parse errors.

    This function is intentionally cheap — it opens the file once and
    closes it immediately.
    """
    try:
        import fitz  # PyMuPDF — imported lazily so conftest loads without it

        doc = fitz.open(pdf_path)
        page = doc[0]
        has_drawings = len(page.get_drawings()) > 0
        has_images = len(page.get_images()) > 0
        doc.close()

        if has_drawings:
            return "vector"
        elif has_images:
            return "raster"
        else:
            return "empty"
    except Exception:
        return "error"


# ---------------------------------------------------------------------------
# Lazy collection helpers
# Call these from test modules instead of running os.listdir at import time.
# ---------------------------------------------------------------------------


def get_vector_pdf_paths() -> list[str]:
    """Return PDF paths from sample_pdfs/vector/ directory."""
    return _list_pdfs_in(_VECTOR_SUBDIR)


def get_raster_pdf_paths() -> list[str]:
    """Return PDF paths from sample_pdfs/raster/ directory."""
    return _list_pdfs_in(_RASTER_SUBDIR)


def get_all_pdf_paths() -> list[str]:
    """Return all PDF paths from both vector and raster subdirectories."""
    return get_vector_pdf_paths() + get_raster_pdf_paths()


def get_categorized_pdf_paths() -> tuple[list[str], list[str], list[str]]:
    """
    Return (all_paths, vector_paths, raster_paths) using subdirectory-based
    discovery (preferred). Falls back to categorize_pdf() on the root dir
    when subdirectories are absent, guarding against missing directories.

    Safe to call at module level — directory checks prevent crashes.
    """
    vector_paths = get_vector_pdf_paths()
    raster_paths = get_raster_pdf_paths()

    # If subdirectories are empty, fall back to root-level discovery + categorization
    if not vector_paths and not raster_paths:
        root_paths = _list_pdfs_flat(_SAMPLE_PDFS_DIR)
        for p in root_paths:
            category = categorize_pdf(p)
            if category == "vector":
                vector_paths.append(p)
            elif category == "raster":
                raster_paths.append(p)

    all_paths = vector_paths + raster_paths
    return all_paths, vector_paths, raster_paths


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def sample_pdfs_dir() -> str:
    """Return path to the sample_pdfs root directory."""
    return _SAMPLE_PDFS_DIR


@pytest.fixture(scope="session")
def vector_pdf_paths() -> list[str]:
    """Session-scoped list of vector PDF paths (may be empty)."""
    return get_vector_pdf_paths()


@pytest.fixture(scope="session")
def raster_pdf_paths() -> list[str]:
    """Session-scoped list of raster PDF paths (may be empty)."""
    return get_raster_pdf_paths()


@pytest.fixture(scope="session")
def all_pdf_paths() -> list[str]:
    """Session-scoped list of all PDF paths (vector + raster)."""
    return get_all_pdf_paths()


@pytest.fixture(scope="session")
def any_pdf_path(
    vector_pdf_paths: list[str], raster_pdf_paths: list[str]
) -> str | None:
    """Return the first available PDF path, or None if no PDFs found."""
    if vector_pdf_paths:
        return vector_pdf_paths[0]
    if raster_pdf_paths:
        return raster_pdf_paths[0]
    return None
