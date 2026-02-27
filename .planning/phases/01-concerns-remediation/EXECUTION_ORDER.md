# Concerns Remediation Execution Order

This checklist defines the recommended execution sequence for all plans in this phase.

## Wave 1 (stabilize quickly)

1. `01-concerns-remediation-01-PLAN.md` - known bugs (semantic extractor logging + Supabase URL validation)
2. `01-concerns-remediation-02-PLAN.md` - API prefix centralization
3. `01-concerns-remediation-03-PLAN.md` - deterministic dependency locking
4. `01-concerns-remediation-04-PLAN.md` - fragile test discovery refactor
5. `01-concerns-remediation-08-PLAN.md` - constraint checker performance optimization

## Wave 2 (security + persistence foundation)

6. `01-concerns-remediation-05-PLAN.md` - auth, CORS, secret safety, request guards
7. `01-concerns-remediation-06-PLAN.md` - DB session + repository layer + infra tests

## Wave 3 (feature integration + generation reliability)

8. `01-concerns-remediation-07-PLAN.md` - persist ingest/generate flows + real status endpoint
9. `01-concerns-remediation-09-PLAN.md` - LLM timeout/retry/backoff + adaptive candidate scheduling

## Wave 4 (scale architecture)

10. `01-concerns-remediation-10-PLAN.md` - async queue worker architecture for heavy jobs

## Dependency Notes

- Plan `07` depends on plans `02` and `06`.
- Plan `09` depends on plan `03`.
- Plan `10` depends on plans `05` and `07`.
- All other plans are independent and can run in parallel within their wave.

## Suggested Milestone Gates

- **Gate A (after Wave 1):** no known bugs, no prefix drift, deterministic deps, stable test collection.
- **Gate B (after Wave 2):** production security baseline enforced and persistence primitives available.
- **Gate C (after Wave 3):** durable ingest/generate/status behavior and improved generation resilience.
- **Gate D (after Wave 4):** heavy workloads are async and status reflects job lifecycle.

## Quick Runbook

Use this pattern for each plan:

```bash
# execute plan
/gsd-execute-phase .planning/phases/01-concerns-remediation/<PLAN_FILE>

# verify changed behavior with plan-specific test commands
pytest <targeted tests from plan>
```

After each plan completes, write:

- `.planning/phases/01-concerns-remediation/<same-name>-SUMMARY.md`
