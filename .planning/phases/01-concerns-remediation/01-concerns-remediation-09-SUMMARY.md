---
phase: 01-concerns-remediation
plan: 09
subsystem: api
tags: [gemini, generation, retry, backoff, timeout, adaptive-fanout, llm]

# Dependency graph
requires:
  - phase: 01-concerns-remediation-03
    provides: "requirements-lock.txt and dependency management baseline"
provides:
  - "Configurable timeout/retry/backoff for Gemini layout generation calls"
  - "Adaptive candidate scheduling that reduces cost under provider failure signals"
  - "Per-config GENERATION_TIMEOUT_SECONDS, GENERATION_MAX_RETRIES, GENERATION_RETRY_BASE_DELAY, GENERATION_RETRY_MAX_DELAY, GENERATION_CANDIDATE_MIN, GENERATION_CANDIDATE_MAX settings"
affects: [generation-pipeline, layout-generator, provider-reliability, cost-control]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bounded retry with exponential backoff using ThreadPoolExecutor wall-clock timeout"
    - "Adaptive fanout: reduce candidates on provider failure, increase on warnings-only, hold on blocking errors"
    - "Config-driven provider resilience: all limits sourced from settings, zero hardcoded values"

key-files:
  created: []
  modified:
    - app/core/config.py
    - app/services/layout_generator.py
    - app/services/generation_pipeline.py
    - tests/test_layout_generator.py
    - tests/test_generation_pipeline.py

key-decisions:
  - "Used ThreadPoolExecutor(max_workers=1).future.result(timeout=N) for wall-clock enforcement — SDK has no native timeout parameter"
  - "Non-transient exceptions (non-RuntimeError) bypass retry immediately to surface SDK errors fast"
  - "Adaptive fanout reduces by 1 on any provider failure rate >0 (cost protection), increases by 1 on warnings-only (quality expansion), holds on blocking errors (feedback prompt handles correction)"
  - "Serial mode (parallel_candidates=1) is always deterministic — no adaptation applied"

patterns-established:
  - "_call_gemini_with_timeout: enforce timeout via executor.future.result(timeout=N)"
  - "_call_gemini_with_retry: loop with exponential backoff, min(base*2^n, max_delay), distinguish transient from permanent errors"
  - "_compute_adaptive_candidates: pure function, testable in isolation, driven by prior constraint result and candidate error count"

requirements-completed: [PERF-02]

# Metrics
duration: 4min
completed: 2026-02-27
---

# Phase 01 Plan 09: Provider Resilience and Adaptive Fanout Summary

**Bounded Gemini call retry with exponential backoff (config-driven) and per-iteration adaptive candidate scheduling based on provider failure rate and violation severity**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-27T11:11:49Z
- **Completed:** 2026-02-27T11:16:43Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added 6 new config settings for provider timeout, retry, backoff, and adaptive fanout bounds
- Implemented `_call_gemini_with_timeout()` using `ThreadPoolExecutor` to enforce wall-clock timeout since the Gemini SDK has no native timeout parameter
- Implemented `_call_gemini_with_retry()` with exponential backoff (delay = min(base * 2^n, max_delay)), distinguishing transient (RuntimeError) from permanent exceptions
- Implemented `_compute_adaptive_candidates()` pure function: reduces fanout on provider failure, expands on warnings-only, holds on blocking errors, clamps to [min, max]
- Added 15 new tests covering all retry/backoff and adaptive fanout scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Add configurable timeout/retry/backoff around Gemini calls** - `78ebf05` (feat)
2. **Task 2: Implement adaptive candidate scheduling in generation pipeline** - `47d7a23` (feat)

## Files Created/Modified
- `app/core/config.py` - Added GENERATION_TIMEOUT_SECONDS, GENERATION_MAX_RETRIES, GENERATION_RETRY_BASE_DELAY, GENERATION_RETRY_MAX_DELAY, GENERATION_CANDIDATE_MIN, GENERATION_CANDIDATE_MAX
- `app/services/layout_generator.py` - Added _call_gemini_with_timeout(), _call_gemini_with_retry(); updated generate_layout() to use them
- `app/services/generation_pipeline.py` - Added _compute_adaptive_candidates(); updated generate_validated_layout() with adaptive scheduling loop
- `tests/test_layout_generator.py` - Added 6 tests: transient retry success, retry exhaustion, non-transient bypass, backoff doubling, delay cap, config propagation
- `tests/test_generation_pipeline.py` - Added 8 tests: serial mode determinism, all adaptive rules, clamp at min/max, first-iteration passthrough

## Decisions Made
- Used `ThreadPoolExecutor(max_workers=1).future.result(timeout=N)` to enforce wall-clock timeout because the Gemini SDK `client.models.generate_content()` has no native timeout parameter
- Non-transient exceptions (anything that is not `RuntimeError`) bypass retry immediately — they surface SDK errors fast rather than retry infinitely
- Adaptive fanout is a pure function (`_compute_adaptive_candidates`) to make it fully unit-testable independent of the pipeline loop

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. New config settings have safe defaults.

## Next Phase Readiness
- Provider resilience controls in place; generation calls are now bounded and will not block indefinitely
- Adaptive fanout reduces unnecessary LLM spend under high-failure conditions
- Plan 10 (the final plan in this phase) can proceed with full generation pipeline stability

## Self-Check: PASSED

All files present and both task commits verified in git log.

---
*Phase: 01-concerns-remediation*
*Completed: 2026-02-27*
