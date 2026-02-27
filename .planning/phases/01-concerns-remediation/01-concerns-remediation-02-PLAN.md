---
phase: 01-concerns-remediation
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - app/core/config.py
  - app/main.py
  - app/api/routes.py
  - tests/test_routes_prefix.py
  - postman/phase2-generate.postman_collection.json
autonomous: true
requirements:
  - TD-02
must_haves:
  truths:
    - "Changing API_V1_PREFIX in settings changes versioned API route mount without editing route decorators"
    - "No hardcoded /v1 fragments remain in API route declarations"
  artifacts:
    - path: app/core/config.py
      provides: "Single source of truth for API prefix"
    - path: app/main.py
      provides: "Blueprint registration derived from settings"
    - path: tests/test_routes_prefix.py
      provides: "Prefix contract tests"
  key_links:
    - from: app/core/config.py
      to: app/main.py
      via: "settings.API_V1_PREFIX"
      pattern: "API_V1_PREFIX"
    - from: app/main.py
      to: app/api/routes.py
      via: "Blueprint mount + relative route definitions"
      pattern: "register_blueprint"
---

<objective>
Centralize API version prefix usage to remove configuration drift.

Purpose: Ensure route versioning changes are done in one place with low regression risk.
Output: Prefix-driven blueprint routing and automated route contract tests.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@app/core/config.py
@app/main.py
@app/api/routes.py
@postman/phase2-generate.postman_collection.json
</context>

<tasks>

<task type="auto">
  <name>Task 1: Derive versioned route mount from settings</name>
  <files>app/core/config.py, app/main.py</files>
  <action>Use settings.API_V1_PREFIX as the canonical version path and compute the blueprint url_prefix so route decorators stay relative and prefix-agnostic. Preserve existing public endpoint paths (`/`, `/health`) and non-versioned namespace behavior where intended.</action>
  <verify>
    <automated>pytest tests/test_generation_endpoint.py::test_generate_layout_success -q</automated>
  </verify>
  <done>Versioned API routing is controlled by one config setting and generation endpoint remains reachable.</done>
</task>

<task type="auto">
  <name>Task 2: Remove hardcoded v1 fragments from API decorators</name>
  <files>app/api/routes.py, postman/phase2-generate.postman_collection.json</files>
  <action>Refactor route decorators to avoid hardcoded `/v1` fragments and align all versioned endpoints with blueprint mount prefix. Update Postman collection paths to match canonical routes after refactor.</action>
  <verify>
    <automated>pytest tests/test_generation_endpoint.py tests/test_ingestion_pipeline.py -q</automated>
  </verify>
  <done>Route declarations are prefix-neutral and existing endpoint tests still pass.</done>
</task>

<task type="auto">
  <name>Task 3: Add explicit prefix contract tests</name>
  <files>tests/test_routes_prefix.py</files>
  <action>Create tests that assert versioned routes resolve under API_V1_PREFIX and fail under stale hardcoded paths. Include a test that monkeypatches API_V1_PREFIX to prove route mount follows settings.</action>
  <verify>
    <automated>pytest tests/test_routes_prefix.py -q</automated>
  </verify>
  <done>Prefix behavior is regression-tested and drift risk is eliminated.</done>
</task>

</tasks>

<verification>
Validate that all versioned endpoints are reachable through API_V1_PREFIX-derived paths and old hardcoded variants are absent.
</verification>

<success_criteria>
TD-02 is resolved and route version changes require editing only settings, not decorators.
</success_criteria>

<output>
After completion, create `.planning/phases/01-concerns-remediation/01-concerns-remediation-02-SUMMARY.md`
</output>
