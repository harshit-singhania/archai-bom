# ArchAI BOM — Claude Guidelines

## 1. The GSD Workflow

This repository uses the **GSD (Get Shit Done)** framework. Before any changes:

1. **Context Initialization**:
   - Read `.planning/STATE.md` — current phase, progress, blockers.
   - Read `.planning/PROJECT.md` — architecture and decisions.

2. **Planning**:
   - Create atomic plans in `.planning/phases/`.
   - Update `EXECUTION_ORDER.md`.

3. **Execution**:
   - Execute in `EXECUTION_ORDER.md` sequence.
   - Atomic commits per plan.

4. **Validation**:
   - Run `pytest` and `./scripts/validate-all.sh`.
   - Create `VERIFICATION.md`.

5. **State Update**:
   - Update `.planning/STATE.md` before ending session.

## 2. Directory-Specific Guidelines

- `app/` — Application code: `app/CLAUDE.md`
- `tests/` — Test suite: `tests/CLAUDE.md`
- `.planning/` — Project plans: `.planning/CLAUDE.md`
- `scripts/` — Utility scripts: `scripts/CLAUDE.md`

## 3. Dev & Test Commands

```bash
pip install -r requirements-lock.txt
pytest -v                         # Verbose test output
pytest -x                         # Stop on first failure
./scripts/validate-all.sh         # Run all validators
```

## 4. Code Style & Architecture

- **Format:** 100 char lines, 4 spaces, double quotes.
- **Imports:** 3 sections (stdlib, third-party, local).
- **Type Hints:** Strictly required. Use `list[str]`, `T | None`.
- **Naming:** `snake_case` functions/vars, `PascalCase` classes.

### Pydantic & SQLModel
- Heavy use of `Field(description="...")`.
- `default_factory=...` for mutable defaults.
- Always specify `__tablename__`.
- DB failures log warnings (non-blocking persistence).

### Architectural Rules
- **No AI in Math Layer:** BOM is deterministic rules only.
- **Async Queue:** Heavy ops (PDF, Gemini) via Redis+RQ; API returns `202` + `job_id`.
- **Error Handling:** Specific exceptions, log with `logger = logging.getLogger(__name__)`, return 4xx/5xx `jsonify()`.
- **Fail Fast:** In production (`DEBUG=False`), fail if `SECRET_KEY` missing.
