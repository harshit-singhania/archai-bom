---
phase: 01-concerns-remediation
plan: 05
type: execute
wave: 2
depends_on:
  - 01-concerns-remediation-02
files_modified:
  - app/core/config.py
  - app/main.py
  - app/api/routes.py
  - .env.example
  - tests/test_security_controls.py
autonomous: true
requirements:
  - SEC-01
  - SEC-02
  - FEAT-02
must_haves:
  truths:
    - "Protected API endpoints reject unauthenticated requests"
    - "CORS policy is origin-restricted by configuration instead of wildcard defaults"
    - "Production startup fails when SECRET_KEY is not explicitly set"
    - "Request size and per-client request rate are bounded"
  artifacts:
    - path: app/main.py
      provides: "Auth middleware, CORS restriction, startup guards, and request limits"
    - path: app/core/config.py
      provides: "Security-relevant environment settings"
    - path: tests/test_security_controls.py
      provides: "Security regression tests for auth/CORS/limits"
  key_links:
    - from: app/core/config.py
      to: app/main.py
      via: "security settings consumption"
      pattern: "API_AUTH_KEY|ALLOWED_ORIGINS|MAX_CONTENT_LENGTH"
    - from: app/main.py
      to: app/api/routes.py
      via: "before_request auth and limiting for /api paths"
      pattern: "before_request"
---

<objective>
Add baseline production security controls around API access and abuse prevention.

Purpose: Prevent anonymous heavy endpoint abuse and unsafe default runtime posture.
Output: API key auth, restrictive CORS, secret key startup guard, payload/rate protections, and tests.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@app/main.py
@app/api/routes.py
@app/core/config.py
@.env.example
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add API key authentication gate for API routes</name>
  <files>app/core/config.py, app/main.py, .env.example</files>
  <action>Add API_AUTH_KEY configuration and enforce it for `/api` requests via middleware (exclude `/health` and `/`). Return 401 JSON for missing/invalid keys. Keep behavior explicit and deterministic for tests and local development with documented opt-out only in DEBUG mode.</action>
  <verify>
    <automated>pytest tests/test_security_controls.py::test_api_requires_auth_key -q</automated>
  </verify>
  <done>Unauthenticated API requests are denied and valid API key requests continue to route handlers.</done>
</task>

<task type="auto">
  <name>Task 2: Enforce CORS restrictions and startup secret key safety</name>
  <files>app/core/config.py, app/main.py, .env.example</files>
  <action>Add ALLOWED_ORIGINS setting and wire CORS to explicit origin allowlist. Add startup guard that raises on missing SECRET_KEY when DEBUG is false to remove fallback secret behavior in production.</action>
  <verify>
    <automated>pytest tests/test_security_controls.py::test_production_requires_secret_key -q</automated>
  </verify>
  <done>CORS is configurable and non-dev startup fails fast without an explicit secret key.</done>
</task>

<task type="auto">
  <name>Task 3: Add payload size and request-rate protections</name>
  <files>app/core/config.py, app/main.py, tests/test_security_controls.py</files>
  <action>Set MAX_CONTENT_LENGTH for upload safety and implement per-client rate limiting for expensive API paths (`ingest`, `generate`) with 429 responses. Keep limiter deterministic and testable in-process.</action>
  <verify>
    <automated>pytest tests/test_security_controls.py -q</automated>
  </verify>
  <done>Oversized payloads and burst traffic are rejected with explicit error responses.</done>
</task>

</tasks>

<verification>
Run security-focused tests and smoke test authenticated access to ingest/generate routes.
</verification>

<success_criteria>
SEC-01, SEC-02, and FEAT-02 are addressed with enforced controls and test coverage.
</success_criteria>

<output>
After completion, create `.planning/phases/01-concerns-remediation/01-concerns-remediation-05-SUMMARY.md`
</output>
