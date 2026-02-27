---
phase: 01-concerns-remediation
plan: 06
type: execute
wave: 2
depends_on:
  - 01-concerns-remediation-03
files_modified:
  - app/core/config.py
  - app/core/database.py
  - app/services/project_repository.py
  - app/services/floorplan_repository.py
  - app/services/bom_repository.py
  - app/core/supabase.py
  - tests/test_repositories.py
  - tests/test_supabase_client.py
autonomous: true
requirements:
  - TD-01
  - TEST-01
must_haves:
  truths:
    - "Application has a reusable DB session layer for persistence operations"
    - "Projects, floorplans, and generated BOMs can be created/read via repository interfaces"
    - "Supabase client lifecycle behavior is covered by tests"
  artifacts:
    - path: app/core/database.py
      provides: "Engine/session factory and transaction-safe session context"
    - path: app/services/project_repository.py
      provides: "Project CRUD access methods"
    - path: app/services/floorplan_repository.py
      provides: "Floorplan CRUD/status update methods"
    - path: app/services/bom_repository.py
      provides: "Generated BOM create/query methods"
  key_links:
    - from: app/core/config.py
      to: app/core/database.py
      via: "DATABASE_URL / Supabase fallback configuration"
      pattern: "DATABASE_URL|SUPABASE"
    - from: app/core/database.py
      to: app/services/floorplan_repository.py
      via: "Session dependency"
      pattern: "Session"
---

<objective>
Build the persistence foundation needed to integrate Supabase-backed state into API flows.

Purpose: Resolve stateless runtime behavior by introducing testable repository boundaries.
Output: DB session module, repository services, and persistence-focused tests.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@app/models/database.py
@app/core/supabase.py
@scripts/setup_supabase_schema.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create database session infrastructure</name>
  <files>app/core/config.py, app/core/database.py</files>
  <action>Add DATABASE_URL-capable settings and implement SQLModel engine/session factory helpers with transaction-safe context manager semantics. Keep implementation test-friendly (in-memory SQLite override support) and avoid direct Supabase SDK dependence for SQLModel operations.</action>
  <verify>
    <automated>pytest tests/test_repositories.py::test_session_factory_uses_test_database -q</automated>
  </verify>
  <done>Session infrastructure supports both local test DB and Supabase/Postgres runtime DB paths.</done>
</task>

<task type="auto">
  <name>Task 2: Implement repository modules for projects/floorplans/BOMs</name>
  <files>app/services/project_repository.py, app/services/floorplan_repository.py, app/services/bom_repository.py</files>
  <action>Create focused repository functions/classes for creating and querying Project, Floorplan, and GeneratedBOM records. Include explicit floorplan status transitions and typed return models to support route integration in later plans.</action>
  <verify>
    <automated>pytest tests/test_repositories.py -q</automated>
  </verify>
  <done>Repository layer provides complete read/write primitives for persistence-aware API flows.</done>
</task>

<task type="auto">
  <name>Task 3: Add infrastructure tests for Supabase and repository behavior</name>
  <files>app/core/supabase.py, tests/test_supabase_client.py, tests/test_repositories.py</files>
  <action>Add tests for get_supabase/reset_supabase_client lifecycle and missing env error paths. Add repository tests for create/read/update status operations using isolated test DB fixtures.</action>
  <verify>
    <automated>pytest tests/test_supabase_client.py tests/test_repositories.py -q</automated>
  </verify>
  <done>Infrastructure and persistence modules have direct automated coverage for happy and failure paths.</done>
</task>

</tasks>

<verification>
Run new infra test modules and ensure repository API is stable for route integration.
</verification>

<success_criteria>
TD-01 persistence foundation exists and TEST-01 high-priority infra coverage gap is closed.
</success_criteria>

<output>
After completion, create `.planning/phases/01-concerns-remediation/01-concerns-remediation-06-SUMMARY.md`
</output>
