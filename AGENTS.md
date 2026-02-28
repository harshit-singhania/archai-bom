# ArchAI BOM — Agent Guidelines

## 1. The GSD Agent Workflow

This repository uses the **GSD (Get Shit Done)** framework. Agents **must** follow this protocol:

1. **Context Initialization**:
   - Always read `.planning/STATE.md` to identify current phase, plan progress, and blockers.
   - Review `.planning/PROJECT.md` for architectural decisions and product goals.

2. **Planning (`gsd-planner`)**:
   - When starting a new phase, create atomic `.md` plans in `.planning/phases/`.
   - Update `EXECUTION_ORDER.md` to define implementation sequence.

3. **Execution (`gsd-executor`)**:
   - Execute plans strictly in `EXECUTION_ORDER.md`.
   - Use atomic commits for each plan.

4. **Validation (`gsd-verifier`)**:
   - Run `pytest` and `./scripts/validate-all.sh`.
   - Create `VERIFICATION.md` proving phase goals met.

5. **State Management**:
   - Update `.planning/STATE.md` to record progress, test metrics, and blockers.

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

- `app/` — Application code: `app/AGENTS.md`
- `tests/` — Test suite: `tests/AGENTS.md`
- `.planning/` — Project plans: `.planning/AGENTS.md`
- `scripts/` — Utility scripts: `scripts/AGENTS.md`

## 4. Dev & Test Commands

```bash
pip install -r requirements-lock.txt
pytest                            # Run all tests
pytest path/to/test.py::test_fn   # Run specific test
./scripts/validate-all.sh         # Run GSD validators
```

## 5. Code Style & Architecture

- **Format:** 100 char lines, 4 spaces, double quotes.
- **Imports:** 3 sections (stdlib, third-party, local) with blank lines.
- **Type Hints:** Required for all params/returns. Use `list[str]`, `T | None`.
- **Naming:** `snake_case` for functions/vars, `PascalCase` for classes.

### Pydantic & SQLModel
- Use `Field(..., description="...")` heavily.
- Use `default_factory=...` for mutable defaults.
- Always specify `__tablename__`.
- DB failures log warnings (non-blocking).

### Architectural Rules
- **No AI in Math Layer:** BOM calculation is deterministic.
- **Async Queue:** Heavy ops run via Redis+RQ; API returns `202 Accepted` + `job_id`.
- **Error Handling:** Specific exceptions, `logger = logging.getLogger(__name__)`, 4xx/5xx `jsonify()` responses.
