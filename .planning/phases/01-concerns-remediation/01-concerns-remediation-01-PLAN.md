---
phase: 01-concerns-remediation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/semantic_extractor.py
  - scripts/setup_supabase_schema.py
  - tests/test_semantic_extractor.py
  - tests/test_setup_supabase_schema.py
autonomous: true
requirements:
  - BUG-01
  - BUG-02
must_haves:
  truths:
    - "Semantic extraction no longer writes debug prints to stdout in runtime path"
    - "Supabase schema setup fails fast with clear error when SUPABASE_PROJECT_URL is missing or malformed"
  artifacts:
    - path: app/services/semantic_extractor.py
      provides: "Logger-based semantic extraction diagnostics"
    - path: scripts/setup_supabase_schema.py
      provides: "Validated project ref parsing before database URL creation"
    - path: tests/test_setup_supabase_schema.py
      provides: "Regression coverage for setup script URL validation"
  key_links:
    - from: app/services/semantic_extractor.py
      to: tests/test_semantic_extractor.py
      via: "assert no print output path"
      pattern: "logger\\.(debug|info|warning|error)"
    - from: scripts/setup_supabase_schema.py
      to: tests/test_setup_supabase_schema.py
      via: "ValueError paths for missing/invalid URL"
      pattern: "get_database_url"
---

<objective>
Remove two known bugs that create noisy logs and unclear setup failures.

Purpose: Stabilize runtime observability and prevent opaque Supabase setup errors.
Output: Semantic extractor logging fix, strict Supabase URL validation, and focused regression tests.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@app/services/semantic_extractor.py
@scripts/setup_supabase_schema.py
@tests/test_semantic_extractor.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace runtime print with structured logging</name>
  <files>app/services/semantic_extractor.py, tests/test_semantic_extractor.py</files>
  <action>Remove the debug print of page dimensions and emit an equivalent logger.debug message instead. Keep failure behavior unchanged (return empty SemanticResult on extraction/Gemini errors). Add or update tests to assert extraction does not depend on stdout side effects.</action>
  <verify>
    <automated>pytest tests/test_semantic_extractor.py -q</automated>
  </verify>
  <done>Semantic extraction uses logger-only diagnostics and semantic extractor tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Add explicit Supabase project URL validation</name>
  <files>scripts/setup_supabase_schema.py, tests/test_setup_supabase_schema.py</files>
  <action>Harden get_database_url by validating SUPABASE_PROJECT_URL is non-empty, HTTPS, and includes a project ref before interpolation. Raise actionable ValueError messages for missing URL, invalid host, and missing password. Add dedicated unit tests for valid and invalid inputs.</action>
  <verify>
    <automated>pytest tests/test_setup_supabase_schema.py -q</automated>
  </verify>
  <done>Setup script surfaces clear validation errors and URL parsing tests cover both happy and failure paths.</done>
</task>

</tasks>

<verification>
Run bug-fix regressions and ensure no existing semantic extraction behavior changed except logging.
</verification>

<success_criteria>
Known bug entries BUG-01 and BUG-02 in CONCERNS.md are fully addressed with automated tests.
</success_criteria>

<output>
After completion, create `.planning/phases/01-concerns-remediation/01-concerns-remediation-01-SUMMARY.md`
</output>
