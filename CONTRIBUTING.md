# Contributing to ArchAI BOM

Thank you for your interest in contributing. This document covers the rules and standards that **every contributor — human or AI — must follow**.

## Table of Contents

- [Getting Started](#getting-started)
- [Code Style](#code-style)
- [Function Rules](#function-rules)
- [Naming Conventions](#naming-conventions)
- [Import Rules](#import-rules)
- [Type Hints](#type-hints)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Commit Messages](#commit-messages)
- [Pull Requests](#pull-requests)
- [Architecture Rules](#architecture-rules)
- [AI-Assisted Contributions](#ai-assisted-contributions)

## Getting Started

```bash
# Clone and install
git clone https://github.com/harshit-singhania/archai-bom.git
cd archai-bom
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-lock.txt

# Verify everything works
pytest
```

## Code Style

### Formatting

| Rule | Value |
|------|-------|
| Line length | **100 characters** max |
| Indentation | **4 spaces** (never tabs) |
| Quotes | **Double quotes** (`"hello"`, not `'hello'`) |
| Trailing whitespace | **None** — remove all trailing whitespace |
| Final newline | **Required** — every file ends with a single newline |

### Blank Lines

- **2 blank lines** between top-level definitions (functions, classes).
- **1 blank line** between method definitions inside a class.
- **No blank line** immediately after a `def` line.
- Use single blank lines within functions to separate logical sections sparingly.

### String Formatting

Use f-strings for simple interpolation. Keep expressions inside `{}` simple — only plain variable and attribute access:

```python
# Good
f"Processing floorplan {floorplan_id}"
f"Found {len(rooms)} rooms in {project.name}"

# Bad — move complex expressions to local variables
f"Area is {width * height * 0.0929} sqm"
f"User {get_user_by_id(uid).name}"

# Good — extract first
area_sqm = width * height * 0.0929
f"Area is {area_sqm} sqm"
```

## Function Rules

### Maximum Length: 50 Lines of Code

No function or method may exceed **50 lines of code** (LOC). Count only executable lines — docstrings, comments, blank lines, and the `def` signature do not count.

**Why:** Long functions hide bugs, resist testing, and are harder to review. Google's style guide recommends ~40 lines. We allow 50 as a hard ceiling.

**If a function exceeds 50 LOC:**
1. Extract helper functions with clear names.
2. Each helper should do one thing.
3. Prefer pure functions (input in, output out, no side effects).

### Maximum Nesting: One Nested Loop

No function may contain **more than one level of nested loops**. A single `for`/`while` inside another `for`/`while` is the maximum.

```python
# Good — single nested loop
def find_adjacent_rooms(rooms: list[Room], walls: list[Wall]) -> dict[str, list[str]]:
    adjacency: dict[str, list[str]] = {}
    for room in rooms:
        for wall in walls:
            if wall.touches(room):
                adjacency.setdefault(room.id, []).append(wall.id)
    return adjacency

# Bad — double nested loop
def bad_function(a, b, c):
    for x in a:
        for y in b:
            for z in c:  # Violation: 2 levels of nesting
                process(x, y, z)

# Good — extract inner logic
def process_pairs(b, c):
    for y in b:
        for z in c:
            process(y, z)

def good_function(a, b, c):
    for x in a:
        process_pairs(b, c)
```

**Alternatives to nested loops:**
- `itertools.product()` for Cartesian products.
- List/dict comprehensions for simple transformations.
- Extract the inner loop into a named helper function.

### Maximum Parameters: 5

Functions should accept **no more than 5 parameters**. If you need more, group related parameters into a dataclass or Pydantic model.

```python
# Bad
def create_bom(width, height, room_type, material_list, rates, units, currency):
    ...

# Good
class RoomSpec(BaseModel):
    width: float
    height: float
    room_type: str

def create_bom(room: RoomSpec, materials: list[MaterialInfo]) -> BOMResult:
    ...
```

### Cyclomatic Complexity: Max 10

No function should have a cyclomatic complexity greater than **10**. Each `if`, `elif`, `for`, `while`, `except`, `and`, `or`, and ternary expression adds 1 to complexity.

**If complexity exceeds 10:**
- Use early returns to flatten nested conditionals.
- Extract conditional branches into helper functions.
- Replace complex conditionals with lookup tables or strategy patterns.

## Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Functions, methods, variables | `snake_case` | `calculate_bom`, `room_area` |
| Classes, Pydantic models | `PascalCase` | `BOMResult`, `FloorplanInput` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT`, `DEFAULT_RATE` |
| Private/internal | Leading underscore | `_parse_walls`, `_db_session` |
| Module files | `snake_case` | `bom_calculator.py`, `job_runner.py` |
| Test files | `test_` prefix | `test_bom_calculator.py` |
| Test functions | `test_` prefix, descriptive | `test_calculate_bom_returns_zero_for_empty_layout` |

### Names to Avoid

- Single-character names (except `i`, `j` in short loops, `x`/`y` for coordinates, `e` for exceptions).
- Abbreviations that aren't universally known (`calc` is fine, `fp` for floorplan is not — use `floorplan`).
- Names that shadow builtins (`id`, `type`, `list`, `dict`, `input`, `map`, `filter`).

## Import Rules

Organize imports into **3 sections** separated by blank lines:

```python
# 1. Standard library
import json
import logging
from pathlib import Path

# 2. Third-party packages
from flask import jsonify, request
from pydantic import BaseModel, Field

# 3. Local application
from app.repositories.job_repository import create_job, get_job
from app.services.bom_calculator import calculate_bom
```

### Import Rules

- **Always use absolute imports** for application code (`from app.services.bom_calculator import ...`).
- **Never use wildcard imports** (`from module import *`).
- **One import per line** for `from` imports when importing 3+ names:
  ```python
  from app.repositories.floorplan_repository import (
      create_floorplan,
      get_floorplan,
      update_floorplan_status,
  )
  ```
- **Remove unused imports** — they add noise and confuse readers.

## Type Hints

Type hints are **required** on all function parameters and return values.

```python
# Good
def calculate_area(width: float, height: float) -> float:
    return width * height

def get_materials(category: str | None = None) -> list[dict[str, Any]]:
    ...

# Bad — missing hints
def calculate_area(width, height):
    return width * height
```

### Type Hint Rules

- Use modern syntax: `list[str]` not `List[str]`, `str | None` not `Optional[str]`.
- Use `Any` sparingly — prefer specific types.
- For Pydantic models, use `Field(..., description="...")` on every field.
- For SQLModel tables, always specify `__tablename__`.

## Error Handling

### Exceptions

- Use **specific exception types** — never bare `except:` or `except Exception:` unless re-raising.
- Define domain exceptions in the service layer (e.g., `IngestValidationError`).
- Controllers catch service exceptions and map them to HTTP status codes.
- **Never silence errors** — at minimum, log them.

```python
# Good
try:
    result = parse_pdf(file_bytes)
except PDFExtractionError as e:
    logger.warning("PDF extraction failed: %s", e)
    return None

# Bad
try:
    result = parse_pdf(file_bytes)
except:
    pass
```

### Logging

- Use `logger = logging.getLogger(__name__)` at module level.
- Use lazy formatting: `logger.info("Processing %s", floorplan_id)` — not f-strings in log calls.
- DB failures are **warnings**, not errors (non-blocking persistence pattern).

## Testing

### Test Structure

Follow **Arrange-Act-Assert**:

```python
def test_bom_includes_flooring_for_office(sample_materials):
    """BOM for office rooms includes flooring materials."""
    # Arrange
    layout = make_layout(rooms=[Room(type="office", area=100.0)])

    # Act
    result = calculate_bom(layout, sample_materials)

    # Assert
    flooring = [item for item in result.line_items if item.category == "flooring"]
    assert len(flooring) > 0
```

### Test Rules

- **One assertion concept per test** — a test can have multiple `assert` statements, but they should all verify one behavior.
- **Descriptive test names**: `test_{what}_{condition}` — e.g., `test_ingest_returns_400_when_no_file_attached`.
- **Mock external services** (Redis, Gemini, PDF libs) — never make real network calls in tests.
- **Mock at the import site**, not the definition site:
  ```python
  # Good — mock where it's imported
  @patch("app.services.ingest_service.create_job")

  # Bad — mock where it's defined
  @patch("app.repositories.job_repository.create_job")
  ```
- **Keep tests fast and deterministic** — no `time.sleep()`, no random data, no real DB calls in unit tests.
- **Use fixtures from `conftest.py`**: `test_db`, `client`, `sample_materials`.

### Running Tests

```bash
pytest                                    # All tests
pytest tests/test_bom_calculator.py -v    # Specific module
pytest -x                                 # Stop on first failure
pytest -k "not test_all_raster"           # Exclude slow parametrized tests
```

## Commit Messages

We follow **[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)**.

### Format

```
<type>(<scope>): <description>

[optional body]
```

### Types

| Type | Use For |
|------|---------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring (no behavior change) |
| `test` | Adding or updating tests |
| `docs` | Documentation changes |
| `chore` | Maintenance (deps, config, CI) |
| `perf` | Performance improvement |
| `style` | Formatting (no logic change) |

### Scopes

Use the area of the codebase affected:

- `api`, `services`, `repositories`, `integrations`, `workers`, `models`, `core`
- `bom`, `ingest`, `generate`, `status`
- Phase names for GSD work: `01-concerns`, `02-bom`, etc.

### Rules

- **Subject line**: Max 72 characters, imperative mood ("add", not "added" or "adds").
- **No period** at the end of the subject line.
- **Body**: Wrap at 100 characters. Explain *what* and *why*, not *how*.
- **One logical change per commit** — don't mix features with refactors.

### Examples

```
feat(bom): add waterproofing materials for bathroom rooms

fix(api): return 400 instead of 500 when PDF file is missing

refactor(services): extract ingestion pipeline from ingest_service

test(repositories): add coverage for concurrent job updates

docs: update CONTRIBUTING.md with PR guidelines
```

## Pull Requests

### Before Opening a PR

1. **Run the test suite** — `pytest` must pass with zero failures.
2. **Check your diff** — `git diff main...HEAD` should contain only intentional changes.
3. **Remove debug code** — no `print()`, `debugger`, `TODO: remove` left behind.
4. **Check import paths** — no stale imports from moved or deleted modules.

### PR Title

Follow the same Conventional Commits format as commit messages:

```
feat(bom): add ceiling material calculations
fix(api): handle missing content-type header gracefully
```

### PR Description

Every PR must include:

1. **Summary** — 1-3 bullet points explaining *what* changed and *why*.
2. **Changes** — List of files or areas modified.
3. **Testing** — How you verified the changes work (test commands, manual steps).
4. **Related** — Link to related issues, plans, or prior PRs if applicable.

### PR Rules

- **Keep PRs small and focused** — one logical change per PR. Avoid mixing features with refactors.
- **No unrelated changes** — don't sneak in formatting fixes or typo corrections alongside feature work. Open a separate PR.
- **All conversations must be resolved** before merging.
- **Tests must pass** — PRs with failing tests will not be merged.
- **Rebase, don't merge** — keep a clean, linear history. Use `git rebase main` before pushing.
- **Squash on merge** — PRs are squash-merged into main. Keep your PR title clean since it becomes the commit message.

### PR Size Guidelines

| Size | Files Changed | Expectation |
|------|---------------|-------------|
| Small | 1-5 | Preferred. Fast to review. |
| Medium | 6-15 | Acceptable. Should be well-described. |
| Large | 16+ | Split if possible. Needs justification. |

## Architecture Rules

### MVC Layer Separation

```
Controllers (api/) -> Services (services/) -> Repositories (repositories/)
                                           -> Integrations (integrations/)
```

- **Controllers** contain zero business logic. Parse request, call service, serialize response.
- **Services** contain all business logic. Raise typed exceptions for controllers to catch.
- **Repositories** handle data access only. Return typed `dict`s, not ORM objects.
- **Integrations** wrap external APIs. If a third-party library changes, only these files change.
- **No skipping layers** — a controller must never import from a repository or integration directly.

### Domain Rules

- **No AI in the math layer** — BOM calculations are deterministic rules only. Construction math cannot hallucinate.
- **Async queue for heavy ops** — PDF ingestion, Gemini calls, and layout generation run via Redis/RQ. API returns `202 Accepted` + `job_id`.
- **Non-blocking persistence** — DB write failures are logged as warnings. The pipeline always returns a result.

## AI-Assisted Contributions

Using AI tools (LLMs, copilots, code generators) is welcome, provided:

1. **You review and understand all generated code** before submitting. You are responsible for the PR, not the tool.
2. **Generated code must meet all standards** in this document — function length, nesting limits, type hints, naming, tests.
3. **Remove AI artifacts** — no `# Generated by AI`, no hallucinated imports, no placeholder comments like `# TODO: implement`.
4. **State AI usage** in the PR description if the PR is substantially AI-generated.
5. **Don't submit low-effort AI PRs** — if the human effort to create the PR is less than the effort to review it, don't submit it.

---

*These standards are enforced on every PR. When in doubt, look at existing code for patterns to follow.*
