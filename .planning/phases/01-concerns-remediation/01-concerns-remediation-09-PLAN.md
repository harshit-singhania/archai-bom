---
phase: 01-concerns-remediation
plan: 09
type: execute
wave: 3
depends_on:
  - 01-concerns-remediation-03
files_modified:
  - app/core/config.py
  - app/services/layout_generator.py
  - app/services/generation_pipeline.py
  - tests/test_generation_pipeline.py
  - tests/test_layout_generator.py
autonomous: true
requirements:
  - PERF-02
must_haves:
  truths:
    - "Generation calls enforce timeout/retry/backoff policy instead of unbounded provider waits"
    - "Parallel candidate count adapts to failure/cost signals within configured limits"
    - "Provider errors degrade gracefully with explicit error messages"
  artifacts:
    - path: app/core/config.py
      provides: "Provider timeout/retry/fanout budget settings"
    - path: app/services/layout_generator.py
      provides: "Timeout/retry wrapper around Gemini call"
    - path: app/services/generation_pipeline.py
      provides: "Adaptive candidate scheduling"
  key_links:
    - from: app/core/config.py
      to: app/services/layout_generator.py
      via: "timeout and retry configuration"
      pattern: "GENERATION_TIMEOUT|GENERATION_RETRY"
    - from: app/services/layout_generator.py
      to: app/services/generation_pipeline.py
      via: "exception signals for adaptive fanout"
      pattern: "RuntimeError|Timeout"
---

<objective>
Control generation cost and latency under external provider variability.

Purpose: Improve reliability and predictability when running multi-candidate LLM layout generation.
Output: Timeout/retry/backoff logic, adaptive fanout controls, and regression tests.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@app/services/layout_generator.py
@app/services/generation_pipeline.py
@tests/test_generation_pipeline.py
@tests/test_layout_generator.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add configurable timeout/retry/backoff around Gemini calls</name>
  <files>app/core/config.py, app/services/layout_generator.py, tests/test_layout_generator.py</files>
  <action>Introduce generation call timeout and retry settings in config, implement bounded retries with exponential backoff in layout_generator, and preserve clear RuntimeError messages after retry exhaustion. Ensure unit tests mock timeout/transient failures and final success/failure behavior.</action>
  <verify>
    <automated>pytest tests/test_layout_generator.py -q</automated>
  </verify>
  <done>Provider calls no longer block indefinitely and transient errors are retried within configured bounds.</done>
</task>

<task type="auto">
  <name>Task 2: Implement adaptive candidate scheduling in generation pipeline</name>
  <files>app/services/generation_pipeline.py, app/core/config.py, tests/test_generation_pipeline.py</files>
  <action>Adjust candidate fanout per iteration based on prior candidate failure rates and violation severity while honoring max worker and budget caps. Keep deterministic single-candidate behavior intact when parallel mode is disabled.</action>
  <verify>
    <automated>pytest tests/test_generation_pipeline.py -q</automated>
  </verify>
  <done>Generation pipeline adapts candidate concurrency to reduce cost and improve completion reliability.</done>
</task>

</tasks>

<verification>
Run generation and layout generator test suites with timeout/retry and adaptive fanout scenarios.
</verification>

<success_criteria>
PERF-02 is resolved with explicit provider resilience controls and adaptive fanout behavior.
</success_criteria>

<output>
After completion, create `.planning/phases/01-concerns-remediation/01-concerns-remediation-09-SUMMARY.md`
</output>
