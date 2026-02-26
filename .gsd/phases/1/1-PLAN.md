---
phase: 1
plan: 1
wave: 1
---

# Plan 1.1: Project Scaffold & PyMuPDF Vector Extraction

## Objective

Stand up the Flask project skeleton and implement the core vector line extraction from CAD-exported PDFs using PyMuPDF. This is the foundation — everything downstream depends on getting raw vector coordinates out of PDFs reliably.

## Context

- .gsd/SPEC.md
- .gsd/RESEARCH.md (Section 1: PDF Ingestion — Vector PDF Bypass)

## Tasks

<task type="auto">
  <name>Scaffold Flask project structure</name>
  <files>
    pyproject.toml
    requirements.txt
    app/__init__.py
    app/main.py
    app/api/__init__.py
    app/api/routes.py
    app/core/__init__.py
    app/core/config.py
    app/services/__init__.py
    app/services/pdf_extractor.py
    tests/__init__.py
    tests/test_pdf_extractor.py
    sample_pdfs/.gitkeep
  </files>
  <action>
    Create project structure:
    - pyproject.toml with project metadata, Python >=3.11
    - requirements.txt: flask, flask-cors, gunicorn, pymupdf (fitz), python-dotenv, pytest, httpx
    - app/main.py: minimal Flask app with health check endpoint GET /health
    - app/core/config.py: Pydantic BaseSettings for environment config
    - app/api/routes.py: Flask blueprint for PDF upload endpoint
    - app/services/pdf_extractor.py: empty module (implemented in next task)
    - tests/test_pdf_extractor.py: empty test file (implemented in next task)
    - sample_pdfs/: directory for test PDFs

    Do NOT:
    - Add Docker, CI/CD, or deployment config (premature for MVP)
    - Add authentication or middleware (not needed yet)
    - Over-engineer the config — keep it minimal
  </action>
  <verify>
    cd app && python -c "from main import app; print(app.name)"
    flask --app app.main run --host 0.0.0.0 --port 5000 & sleep 2 && curl http://localhost:5000/health && kill %1
  </verify>
  <done>Flask app starts, /health returns 200 OK</done>
</task>

<task type="auto">
  <name>Implement PyMuPDF vector line extraction</name>
  <files>
    app/services/pdf_extractor.py
    app/models/__init__.py
    app/models/geometry.py
  </files>
  <action>
    Implement the Vector Extractor from RESEARCH.md:

    1. app/models/geometry.py — Define Pydantic models:
       - VectorLine: x1, y1, x2, y2, width (line thickness), color (RGB tuple)
       - ExtractionResult: list of VectorLine objects, page_width, page_height, metadata

    2. app/services/pdf_extractor.py — Implement extract_vectors(pdf_path: str, page_num: int = 0) -> ExtractionResult:
       - Open PDF with fitz.open(pdf_path)
       - Get page via doc[page_num]
       - Extract all vector drawings via page.get_drawings()
       - For each drawing, extract line segments (items with type "l" for line)
       - Capture line coordinates, stroke width, and color
       - Return ExtractionResult with all vector lines

    Do NOT:
    - Filter or classify lines yet (that's Plan 1.2)
    - Call any external AI API
    - Handle multi-page PDFs (extract from page 0 only for MVP)
  </action>
  <verify>
    pytest tests/test_pdf_extractor.py -v
  </verify>
  <done>
    Given a sample CAD-exported PDF in sample_pdfs/:
    - extract_vectors() returns a non-empty list of VectorLine objects
    - Each VectorLine has valid x1,y1,x2,y2 coordinates and width > 0
    - Test passes with assertion on line count > 0
  </done>
</task>

<task type="checkpoint:human-verify">
  <name>Verify extraction against a real floorplan PDF</name>
  <files>sample_pdfs/</files>
  <action>
    User places a real CAD-exported A-series floorplan PDF into sample_pdfs/.
    Run extraction and print summary: total lines extracted, coordinate ranges, thickness distribution.
    User visually confirms that the line count and coordinate ranges are plausible for the floorplan.
  </action>
  <verify>
    python -c "
    from app.services.pdf_extractor import extract_vectors
    result = extract_vectors('sample_pdfs/test_floorplan.pdf')
    print(f'Lines: {len(result.lines)}')
    print(f'Page: {result.page_width}x{result.page_height}')
    widths = set(round(l.width, 2) for l in result.lines)
    print(f'Unique line widths: {widths}')
    "
  </verify>
  <done>User confirms extracted line count and dimensions are plausible for the source PDF</done>
</task>

## Success Criteria

- [ ] Flask project runs and serves /health endpoint
- [ ] PyMuPDF extracts vector lines from a CAD-exported PDF with correct coordinates
- [ ] Line width and color metadata are captured for downstream filtering
- [ ] At least one real floorplan PDF tested with plausible results
