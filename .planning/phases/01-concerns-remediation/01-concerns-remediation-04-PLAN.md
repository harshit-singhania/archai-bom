---
phase: 01-concerns-remediation
plan: 04
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/test_ingestion_pipeline.py
  - tests/test_semantic_extractor.py
  - tests/test_wall_detector.py
  - tests/test_pdf_extractor.py
autonomous: true
requirements:
  - FRAG-01
must_haves:
  truths:
    - "Test discovery does not fail when sample PDF directories are missing or empty"
    - "PDF categorization happens lazily through fixtures, not at import time"
  artifacts:
    - path: tests/conftest.py
      provides: "Shared fixture helpers for PDF discovery/categorization"
    - path: tests/test_ingestion_pipeline.py
      provides: "Fixture-based PDF selection"
    - path: tests/test_semantic_extractor.py
      provides: "Fixture-based PDF selection"
  key_links:
    - from: tests/conftest.py
      to: tests/test_ingestion_pipeline.py
      via: "fixture injection"
      pattern: "@pytest.fixture"
    - from: tests/conftest.py
      to: tests/test_pdf_extractor.py
      via: "shared categorization helper"
      pattern: "categorize_pdf|vector_pdfs|raster_pdfs"
---

<objective>
Remove import-time filesystem coupling from integration-heavy test modules.

Purpose: Make test collection robust across environments with partial fixture sets.
Output: Shared lazy fixtures and refactored test modules using fixture injection.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@tests/test_ingestion_pipeline.py
@tests/test_semantic_extractor.py
@tests/test_wall_detector.py
@tests/test_pdf_extractor.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Introduce shared PDF discovery fixtures</name>
  <files>tests/conftest.py</files>
  <action>Create fixtures/helpers that safely locate sample PDFs and classify vector/raster inputs with graceful fallback when directories or files are absent. Keep helper APIs reusable across multiple test modules.</action>
  <verify>
    <automated>pytest tests/test_pdf_extractor.py::TestPDFCategorization::test_categorization_accuracy -q</automated>
  </verify>
  <done>Shared fixtures exist and can categorize fixtures without import-time side effects.</done>
</task>

<task type="auto">
  <name>Task 2: Refactor integration-heavy modules to use fixtures</name>
  <files>tests/test_ingestion_pipeline.py, tests/test_semantic_extractor.py, tests/test_wall_detector.py, tests/test_pdf_extractor.py</files>
  <action>Replace module-level os.listdir/categorization blocks with fixture-driven setup. Preserve current test intent and markers, but avoid any expensive or fragile computation during module import.</action>
  <verify>
    <automated>pytest tests/test_ingestion_pipeline.py tests/test_semantic_extractor.py tests/test_wall_detector.py tests/test_pdf_extractor.py -q</automated>
  </verify>
  <done>All four modules collect and run successfully with fixture-driven data discovery.</done>
</task>

</tasks>

<verification>
Run collection and execution of the four previously fragile modules in a clean environment.
</verification>

<success_criteria>
FRAG-01 is resolved with no import-time filesystem scanning in target modules.
</success_criteria>

<output>
After completion, create `.planning/phases/01-concerns-remediation/01-concerns-remediation-04-SUMMARY.md`
</output>
