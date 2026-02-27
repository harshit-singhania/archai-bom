---
phase: 01-concerns-remediation
plan: 08
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/constraint_checker.py
  - tests/test_constraint_checker.py
  - tests/test_constraint_checker_performance.py
autonomous: true
requirements:
  - PERF-01
must_haves:
  truths:
    - "Constraint validation remains functionally equivalent while avoiding full pairwise intersection checks"
    - "Room and fixture overlap checks use indexed candidate selection"
  artifacts:
    - path: app/services/constraint_checker.py
      provides: "Spatial-index assisted collision checks (STRtree + bbox prefilter)"
    - path: tests/test_constraint_checker_performance.py
      provides: "Performance regression benchmark harness"
  key_links:
    - from: app/services/constraint_checker.py
      to: tests/test_constraint_checker.py
      via: "behavioral regression assertions"
      pattern: "validate_layout"
    - from: app/services/constraint_checker.py
      to: tests/test_constraint_checker_performance.py
      via: "timing envelope verification"
      pattern: "STRtree"
---

<objective>
Reduce constraint checker computational cost for large layouts.

Purpose: Improve generation throughput by removing unnecessary O(n^2) geometry intersections.
Output: Indexed overlap checks and performance regression coverage.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@app/services/constraint_checker.py
@tests/test_constraint_checker.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Introduce STRtree-backed candidate filtering</name>
  <files>app/services/constraint_checker.py</files>
  <action>Refactor room and fixture overlap loops to use Shapely STRtree or equivalent spatial index, and prefilter by bounding box overlap before expensive polygon intersection. Keep violation semantics and tolerance thresholds unchanged.</action>
  <verify>
    <automated>pytest tests/test_constraint_checker.py -q</automated>
  </verify>
  <done>Constraint checker logic is index-assisted and existing behavior tests pass unchanged.</done>
</task>

<task type="auto">
  <name>Task 2: Add performance regression test for high-entity layouts</name>
  <files>tests/test_constraint_checker_performance.py</files>
  <action>Create a synthetic large-layout benchmark test that compares runtime against a fixed envelope and verifies no timeout/degenerate slowdown under representative high room/fixture counts.</action>
  <verify>
    <automated>pytest tests/test_constraint_checker_performance.py -q</automated>
  </verify>
  <done>Performance envelope is covered by automated tests and prevents accidental quadratic regressions.</done>
</task>

</tasks>

<verification>
Run functional and performance suites for constraint validation.
</verification>

<success_criteria>
PERF-01 is resolved with indexed geometry checks and automated perf guardrails.
</success_criteria>

<output>
After completion, create `.planning/phases/01-concerns-remediation/01-concerns-remediation-08-SUMMARY.md`
</output>
