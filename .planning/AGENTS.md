# ArchAI BOM — Agent Guidelines (.planning/)

## Context

You are in the `.planning/` directory containing project plans and state.

## GSD Workflow (CRITICAL)

**This directory IS the GSD framework. Follow strictly:**

1. **Context Initialization**:
   - Read `STATE.md` — current phase, progress, blockers
   - Read `PROJECT.md` — architecture and decisions
   - Read `../AGENTS.md` — full guidelines

2. **Planning Phase**:
   - Create plans in `phases/XX-phase-name/`
   - Use format: `XX-phase-name-NN-PLAN.md`
   - Update `EXECUTION_ORDER.md` with sequence
   - Plans must be atomic and verifiable

3. **Execution Phase**:
   - Execute plans in `EXECUTION_ORDER.md` sequence
   - Create `XX-phase-name-NN-SUMMARY.md` after each plan
   - Update `STATE.md` with progress

4. **Validation Phase**:
   - Create `VERIFICATION.md` proving phase goals met
   - Update `STATE.md` with test metrics

5. **State Management**:
   - Update `STATE.md` after EVERY session
   - Record: completed plans, test metrics, blockers, decisions

## Directory Structure

```
.planning/
├── PROJECT.md          # Core architecture and decisions
├── ROADMAP.md          # Milestones and phases
├── STATE.md            # Current status (ALWAYS READ FIRST)
├── EXECUTION_ORDER.md  # Plan execution sequence
├── phases/
│   ├── 01-concerns-remediation/
│   └── 02-bom-calculator-engine/
└── codebase/           # Architecture documentation
```

## Plan File Format

```markdown
# Plan N: Title

**Goal:** One-line objective
**Depends on:** Previous plans
**Success Criteria:**
1. Measurable criterion 1
2. Measurable criterion 2

## Tasks
- [ ] Task 1
- [ ] Task 2
```

## Summary File Format

```markdown
---
phase: XX-phase-name
plan: N
status: completed
---

# Plan N Summary

## Delivered
- Item 1
- Item 2

## Verification
- Tests: X passed
```

## NEVER

- Skip reading `STATE.md`
- Modify plans without updating `STATE.md`
- Leave a session without updating `STATE.md`

## References

- Root: `../AGENTS.md`
- Root: `../CLAUDE.md`
- Code: `../app/AGENTS.md`
