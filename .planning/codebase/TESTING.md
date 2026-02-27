# Testing Patterns

**Analysis Date:** 2026-02-27

## Test Framework

**Runner:**
- pytest >=8.0.0 (declared in `requirements.txt`)
- Config: Not detected (`pytest.ini`/`pyproject.toml` absent)

**Assertion Library:**
- Native `assert` statements with `pytest` helpers (`pytest.raises`, markers, fixtures)

**Run Commands:**
```bash
pytest                              # Run all tests
pytest -k generation_pipeline       # Filter by keyword
pytest tests/test_generation_endpoint.py -q   # Run single module quietly
```

## Test File Organization

**Location:**
- Separate top-level `tests/` directory (not co-located with source)

**Naming:**
- `test_<feature>.py` naming in `tests/` (for example `tests/test_constraint_checker.py`)

**Structure:**
```text
tests/
  test_generation_endpoint.py
  test_generation_pipeline.py
  test_constraint_checker.py
  test_layout_generator.py
  test_ingestion_pipeline.py
  ...
```

## Test Structure

**Suite Organization:**
```python
@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client

@patch("app.api.routes.generate_validated_layout")
def test_generation_endpoint_success(mock_generate_validated_layout, client):
    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 200
```

**Patterns:**
- Setup pattern: helper payload builders (`_request_payload`, `_layout`, `_base_layout_payload`) and local fixtures
- Teardown pattern: context-managed Flask clients and temporary files via `tmp_path` fixtures
- Assertion pattern: validate HTTP status + key payload fields + model constraints

## Mocking

**Framework:** `unittest.mock.patch` + `pytest` `monkeypatch`

**Patterns:**
```python
@patch("app.services.layout_generator.genai.Client")
def test_generate_layout_success(mock_genai_client, monkeypatch):
    monkeypatch.setattr(
        "app.services.layout_generator.settings.GOOGLE_API_KEY", "test_key"
    )
    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client
```

**What to Mock:**
- External AI calls (`genai.Client`) in `tests/test_layout_generator.py`, `tests/test_raster_wall_extractor.py`, and `tests/test_semantic_extractor.py`
- Externalized app settings via `monkeypatch` when testing key-dependent code paths
- I/O-heavy operations (`fitz.open`) for isolated unit tests

**What NOT to Mock:**
- Pure geometry/domain logic where deterministic behavior is expected (`tests/test_grid_snapper.py`, `tests/test_constraint_checker.py`)

## Fixtures and Factories

**Test Data:**
```python
def _valid_layout_payload() -> dict:
    return {
        "rooms": [...],
        "interior_walls": [...],
        "doors": [...],
        "fixtures": [...],
        "page_dimensions_mm": (10000.0, 8000.0),
    }
```

**Location:**
- Inline helper builders inside each test module (no shared `conftest.py` detected)
- Binary fixture corpus in `sample_pdfs/raster/` and `sample_pdfs/vector/`

## Coverage

**Requirements:** None enforced (no coverage threshold config detected)

**View Coverage:**
```bash
pytest --cov=app --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Model validation and pure utility tests in `tests/test_layout_models.py`, `tests/test_grid_snapper.py`, and portions of `tests/test_pdf_extractor.py`

**Integration Tests:**
- Flask endpoint flows with test client in `tests/test_generation_endpoint.py` and `tests/test_ingestion_pipeline.py`
- Real fixture PDFs with partial mocking in `tests/test_raster_wall_extractor.py` and `tests/test_semantic_extractor.py`

**E2E Tests:**
- Not used (no browser/system-level workflow harness detected)

## Common Patterns

**Async Testing:**
```python
# Not used; tests are synchronous Flask/service calls.
```

**Error Testing:**
```python
with pytest.raises(ValueError, match="non-JSON response"):
    generate_layout(spatial_graph=graph, prompt="simple clinic")

response = client.post("/api/v1/generate", json=payload)
assert response.status_code == 400
assert "prompt" in response.get_json()["error"]
```

---

*Testing analysis: 2026-02-27*
