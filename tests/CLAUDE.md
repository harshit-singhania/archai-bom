# ArchAI BOM — Claude Guidelines (tests/)

## Context

You are in the `tests/` directory containing the test suite.

## GSD Workflow (MANDATORY)

**ALWAYS follow GSD for test work:**

1. **Context**:
   - Read `../.planning/STATE.md` — test requirements for current phase
   - Read `../CLAUDE.md` — full guidelines
   - Check existing test patterns in this directory

2. **Planning**:
   - Define what needs test coverage
   - Plan test cases: happy path, edge cases, error cases
   - Update `.planning/STATE.md` with test plan

3. **Execution**:
   - Follow existing test structure and naming
   - Use fixtures from `conftest.py`
   - Mock external dependencies
   - Keep tests deterministic

4. **Validation**:
   - Run `pytest` — all tests must pass
   - Run `./scripts/validate-all.sh`
   - Update `.planning/STATE.md` with test metrics

## Test Patterns

### Repository Tests
```python
def test_create_returns_integer_id(test_db):
    """Repository creates should return positive int IDs."""
    result = create_item(data="test")
    assert isinstance(result, int)
    assert result > 0
```

### API Contract Tests
```python
@patch("app.services.ingest_service.enqueue_ingest_job")
@patch("app.services.ingest_service.create_job")
def test_endpoint_returns_202(mock_create, mock_enqueue, client):
    """Async endpoints return 202 with job_id."""
    mock_create.return_value = 42
    response = client.post("/api/v1/ingest", ...)
    assert response.status_code == 202
```

### Mock Patch Paths (MVC)
After the MVC refactor, mock paths target where the name is **imported**, not defined:
- Ingest mocks: `app.services.ingest_service.create_job`, `app.services.ingest_service.enqueue_ingest_job`
- Generate mocks: `app.services.generate_service.create_job`, `app.services.generate_service.enqueue_generate_job`
- Job runner mocks: `app.workers.job_runner.ingest_pdf`, `app.workers.job_runner.update_floorplan_*`
- Integration mocks: `app.integrations.layout_generator.*`, `app.integrations.semantic_extractor.*`

### BOM Calculator Tests
```python
def test_geometry_drives_quantity(sample_materials, layout):
    """BOM quantities derived from layout geometry."""
    result = calculate_bom(layout, sample_materials)
    flooring = [i for i in result.line_items if i.category == "flooring"]
    assert len(flooring) > 0
```

## Fixtures (from conftest.py)

- `test_db` — Supabase-backed isolated DB session
- `client` — Flask test client
- `sample_materials` — Material catalog fixture

## Key Principles

- **Mock external services** (Redis, Gemini, PDF libs)
- **Test behavior, not implementation**
- **One concept per test**
- **Descriptive names**: `test_*_when_*`
- **Fast and deterministic** — no real network calls

## References

- Full: `../CLAUDE.md`
- Agent: `../AGENTS.md`
- App: `../app/CLAUDE.md`
