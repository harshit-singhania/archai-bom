# ArchAI BOM — Claude Guidelines (app/)

## Context

You are in the `app/` directory containing the core Flask application.

## GSD Workflow (MANDATORY)

**ALWAYS follow the GSD framework:**

1. **Context Initialization** (BEFORE any changes):
   - Read `../.planning/STATE.md` — understand current phase and progress
   - Read `../.planning/PROJECT.md` — understand architecture
   - Read `../CLAUDE.md` — full Claude guidelines

2. **Planning Phase**:
   - Use `/gsd-plan-phase` to break work into atomic plans
   - Store plans in `.planning/phases/`
   - Update `EXECUTION_ORDER.md`

3. **Execution Phase**:
   - Use `/gsd-execute-plan path/to/PLAN.md`
   - Atomic commits per plan
   - Follow existing code patterns

4. **Validation Phase**:
   - Run `pytest` — all tests must pass
   - Run `./scripts/validate-all.sh`
   - Create `VERIFICATION.md` report

5. **State Update**:
   - Update `.planning/STATE.md` with progress
   - Record metrics, blockers, decisions

## app/ Specific Guidance

### API Layer (`api/`)
- Routes return `202 Accepted` for async operations
- Use `jsonify()` for all responses
- Validate inputs with Pydantic models
- Return 4xx/5xx with descriptive error messages

### Services Layer (`services/`)
- **Repository pattern**: `get_*`, `create_*`, `update_*`, `list_*`
- Return typed `dict`s, not ORM objects
- DB failures log warnings, don't crash pipeline
- `bom_calculator.py` — pure deterministic math, no AI

### Models Layer (`models/`)
- Pydantic for API schemas, SQLModel for DB tables
- Heavy use of `Field(description="...")`
- `__tablename__` required for SQLModel

### Workers Layer (`workers/`)
- RQ-based background jobs
- `enqueue_*` functions for API to call
- Jobs marked as `running` before execution
- Never re-raise exceptions; mark `failed` instead

## Critical Rules

- **No AI in BOM math** — deterministic geometry rules only
- **Non-blocking persistence** — DB failures are warnings
- **Type safety** — strict hints on all functions
- **100 char lines** — format consistently

## References

- Full guidelines: `../CLAUDE.md`
- Agent guidelines: `../AGENTS.md`
- Testing: `../tests/CLAUDE.md`
