# ArchAI BOM — Agent Guidelines (app/)

## Context

You are in the `app/` directory containing the core application code.

## GSD Workflow (REQUIRED)

**CRITICAL:** Before making any changes:

1. Read `../.planning/STATE.md` — current phase, plan progress, blockers
2. Read `../.planning/PROJECT.md` — architectural decisions, product goals
3. Read `../AGENTS.md` — full agent guidelines
4. Follow the GSD execution protocol:
   - Planning: Create atomic `.md` plans in `.planning/phases/`
   - Execution: Use `/gsd-execute-plan path/to/PLAN.md`
   - Validation: Run `pytest` and `./scripts/validate-all.sh`
   - State: Update `.planning/STATE.md` before ending session

## MVC Architecture

```
app/
├── api/            # Controllers — HTTP parsing, response serialization, zero business logic
├── services/       # Services — business logic, orchestration, domain rules, pipelines
├── repositories/   # Repositories — data access only, return typed dicts, not ORM objects
├── integrations/   # Integrations — external API adapters (Gemini, PyMuPDF)
├── workers/        # Workers — Redis/RQ queue infrastructure + job runner dispatch
├── models/         # Models — Pydantic schemas + SQLModel ORM tables
└── core/           # Core — config, database engine/session management
```

**Layer rules:** Controllers → Services → Repositories/Integrations. No skipping layers.

## Key Conventions

- **100 char line limit**, 4 spaces, double quotes
- **3 import sections**: stdlib, third-party, local (blank lines between)
- **Type hints required**: `list[str]`, `T | None` (not `Optional[T]`)
- **Pydantic**: Use `Field(..., description="...")` heavily
- **SQLModel**: Always specify `__tablename__`
- **No AI in math layer**: BOM calculations are deterministic rules only
- **Async pattern**: Heavy ops return `202 Accepted` + `job_id`
- **Error handling**: Log warnings for DB failures (non-blocking), specific exceptions

## Testing

```bash
pytest tests/                    # All tests
pytest tests/test_bom_calculator.py -v  # Specific module
```

## Related Guidelines

- Root: `../AGENTS.md` — full guidelines
- Root: `../CLAUDE.md` — Claude-specific guidelines
- Tests: `../tests/AGENTS.md` — testing guidelines
