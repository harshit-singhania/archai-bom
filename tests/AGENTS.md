# ArchAI BOM — Agent Guidelines (tests/)

## Context

You are in the `tests/` directory containing the test suite.

## GSD Workflow (REQUIRED)

**CRITICAL:** Before modifying tests:

1. Read `../.planning/STATE.md` — current phase and test requirements
2. Read `../.planning/PROJECT.md` — understand what needs testing
3. Read `../AGENTS.md` — full agent guidelines
4. Follow GSD protocol for test changes:
   - Plan: Define test coverage requirements
   - Execute: Write tests matching existing patterns
   - Validate: Run `pytest` — all must pass
   - State: Update `.planning/STATE.md` with test metrics

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures (test_db, client)
├── test_async_jobs.py       # Job lifecycle and worker tests
├── test_bom_calculator.py   # BOM deterministic math tests
├── test_bom_integration.py  # End-to-end BOM flow tests
├── test_generation_endpoint.py  # API contract tests
├── test_repositories.py     # DB repository tests
├── test_status_endpoint.py  # Status API tests
└── ...
```

## Testing Conventions

- **pytest** as test runner
- **Fixtures in conftest.py**: `test_db`, `client`, `sample_materials`
- **Mock external services**: Redis, Gemini, PDF extraction
- **Test DB isolation**: Supabase-backed, auto-truncated per test
- **Descriptive test names**: `test_*_returns_*_when_*`
- **One assertion concept per test**

## Writing Tests

```python
def test_feature_behavior(test_db):
    """Clear docstring explaining what is tested."""
    # Arrange
    input_data = {...}
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result.status == "expected"
```

## Running Tests

```bash
pytest                           # All tests
pytest -v                       # Verbose
pytest -x                       # Stop on first failure
pytest tests/test_bom_calculator.py -v  # Specific file
pytest -k "test_pattern"        # Pattern match
```

## References

- Root: `../AGENTS.md` — full guidelines
- Root: `../CLAUDE.md` — Claude-specific guidelines
- App: `../app/AGENTS.md` — application code guidelines
