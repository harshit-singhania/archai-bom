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

## 2. MVC Architecture

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

## 3. Directory-Specific Guidelines

- `app/` — Application code: `app/CLAUDE.md`
- `tests/` — Test suite: `tests/CLAUDE.md`
- `.planning/` — Project plans: `.planning/CLAUDE.md`
- `scripts/` — Utility scripts: `scripts/CLAUDE.md`

## 4. Dev & Test Commands

```bash
pip install -r requirements-lock.txt
pytest -v                         # Verbose test output
pytest -x                         # Stop on first failure
./scripts/validate-all.sh         # Run all validators
```

## 5. Code Style & Architecture

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full coding standards, commit message format, and PR guidelines. Key rules:

- **Format:** 100 char lines, 4 spaces, double quotes.
- **Functions:** Max **50 LOC**, max **1 nested loop**, max **5 parameters**.
- **Imports:** 3 sections (stdlib, third-party, local).
- **Type Hints:** Strictly required. Use `list[str]`, `T | None`.
- **Naming:** `snake_case` functions/vars, `PascalCase` classes.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) — `type(scope): description`.

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
