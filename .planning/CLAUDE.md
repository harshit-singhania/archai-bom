# ArchAI BOM — Claude Guidelines (.planning/)

## Context

You are in the `.planning/` directory — the GSD framework control center.

## GSD Workflow (ABSOLUTE REQUIREMENT)

**This is where project state lives. Follow EXACTLY:**

### 1. Context (ALWAYS FIRST)
```
READ STATE.md → READ PROJECT.md → READ ../CLAUDE.md
```

### 2. Planning
- Create: `phases/XX-name/XX-name-NN-PLAN.md`
- Update: `EXECUTION_ORDER.md`
- Define: Success criteria (measurable)

### 3. Execution
- Follow `EXECUTION_ORDER.md` sequence
- Create: `XX-name-NN-SUMMARY.md` per plan
- Atomic commits

### 4. Validation
- Run: `pytest`, `./scripts/validate-all.sh`
- Create: `VERIFICATION.md`
- Prove: Success criteria met

### 5. State Update (MANDATORY)
Update `STATE.md` with:
- Completed plans
- Test metrics
- Blockers
- Decisions

## File Standards

### STATE.md
```yaml
---
status: in_progress
last_updated: "2026-02-28T18:20:00Z"
---

# Current Position
Phase: N of M
Plan: X of Y
```

### PLAN.md
- Clear goal
- Dependencies listed
- Success criteria (measurable)
- Atomic tasks

### SUMMARY.md
- What was delivered
- Test results
- Deviations noted
- Files changed

## Critical Rules

1. **ALWAYS read STATE.md first**
2. **NEVER leave session without updating STATE.md**
3. **Plans must be atomic** (one focus)
4. **Success criteria must be testable**
5. **Update STATE.md after every plan**

## Phase Status Values

- `planned` — Not started
- `in_progress` — Currently executing
- `completed` — All plans done, verified
- `blocked` — Has blockers

## References

- Full: `../CLAUDE.md`
- Agent: `../AGENTS.md`
- Code: `../app/CLAUDE.md`
