Everything in this file is optional. For canonical rules, see `PROJECT_RULES.md`.

# Claude.md

Claude-specific execution notes for this repo, optimized for low token usage.

## 1) Minimal Load Order
- Start with `.gsd/STATE.md` and `.gsd/ROADMAP.md`
- If planning/execution is needed, read only the relevant workflow file in `.agent/workflows/`
- Read only files tied to the active task (use search-first discipline)

## 2) Canonical GSD Behavior
- Enforce Planning Lock (`SPEC.md` must be `FINALIZED` before coding)
- Follow `SPEC -> PLAN -> EXECUTE -> VERIFY -> COMMIT`
- Keep plans atomic (2-3 tasks each)
- Verify with empirical proof (tests/command outputs), not reasoning claims

## 3) Extended Thinking Mode

Activate extended thinking for:

| Task Type | Recommended |
|-----------|-------------|
| Architecture planning | ✅ High effort |
| Complex debugging | ✅ High effort |
| Security analysis | ✅ High effort |
| Simple edits | ❌ Not needed |
| Quick iterations | ❌ Overhead too high |

### Effort Levels

| Level | Use Case |
|-------|----------|
| `low` | Simple edits, formatting, comments |
| `medium` | Standard implementation (default) |
| `high` | Complex logic, refactoring, debugging |
| `max` | Architecture, security, critical decisions |

**Default:** `medium` if not specified.

## 4) GSD Workflow is MANDATORY

The workflows in `.agent/workflows/` are **core to how this codebase operates**. They are not suggestions.

### 4.1 Required Workflow Commands

| Command | File | Purpose |
|---------|------|---------|
| `/new-project` | `.agent/workflows/new-project.md` | Initialize SPEC → ROADMAP |
| `/map` | `.agent/workflows/map.md` | Brownfield codebase analysis |
| `/plan N` | `.agent/workflows/plan.md` | Create executable phase plans |
| `/execute N` | `.agent/workflows/execute.md` | Execute plans by wave |
| `/verify N` | `.agent/workflows/verify.md` | Empirical validation |
| `/debug` | `.agent/workflows/debug.md` | Systematic debugging |
| `/pause` | `.agent/workflows/pause.md` | Session handoff |
| `/resume` | `.agent/workflows/resume.md` | Session restoration |
| `/progress` | `.agent/workflows/progress.md` | Status check |

### 4.2 Required Skills

Skills in `.agent/skills/` define detailed methodologies:

| Skill | File | Use When |
|-------|------|----------|
| Planner | `.agent/skills/planner/SKILL.md` | Creating/reviewing plans |
| Executor | `.agent/skills/executor/SKILL.md` | Executing tasks |
| Verifier | `.agent/skills/verifier/SKILL.md` | Validating work |
| Debugger | `.agent/skills/debugger/SKILL.md` | Debugging failures |
| Codebase Mapper | `.agent/skills/codebase-mapper/SKILL.md` | Mapping brownfield code |

### 4.3 Key GSD Principles for Claude

**Plans Are Prompts** — PLAN.md IS the prompt. It contains objective, context, tasks, verification.

**Aggressive Atomicity** — Each plan: **2-3 tasks max**. No exceptions.

**Context Quality Thresholds:**
- 0-30%: PEAK quality
- 30-50%: GOOD quality (target zone)
- 50-70%: DEGRADING (efficiency mode)
- 70%+: POOR (avoid)

**Automation-First Rule:** If Claude CAN do it via CLI/API, Claude MUST do it. Checkpoints are for verification AFTER automation.

### 4.4 Deviation Rules (Apply Automatically)

When executing tasks, apply these rules:

| Rule | Trigger | Claude Action |
|------|---------|---------------|
| **Rule 1: Bug** | Code doesn't work | Auto-fix inline, document in SUMMARY |
| **Rule 2: Missing Critical** | No validation/auth/etc | Auto-add, document in SUMMARY |
| **Rule 3: Blocking** | Missing deps/broken imports | Auto-fix, document in SUMMARY |
| **Rule 4: Architectural** | New tables, breaking changes | STOP → checkpoint → user decision |

**Priority:** Rule 4 > Rules 1-3. When in doubt, checkpoint.

## 5) Repo-Specific Hot Paths

### API Layer
- **Ingest endpoint**: `app/api/routes.py` — `ingest_floorplan()` handles multipart upload, temp file cleanup, calls `ingest_pdf()`, returns `model_dump()` JSON
- **Health check**: `app/main.py` — `health_check()` returns `{"status": "ok", "version"}`

### Service Layer
- **Pipeline**: `app/services/ingestion_pipeline.py` — Single function `ingest_pdf(pdf_path) -> WallDetectionResult`; tries vector extraction first, falls back to `extract_walls_from_raster()` if no vectors found
- **PDF parsing**: `app/services/pdf_extractor.py` — `extract_vectors()` uses PyMuPDF `page.get_drawings()`; handles `"l"` (line) and `"re"` (rectangle) items; coordinates in PDF points (1/72 inch)
- **Wall detection**: `app/services/wall_detector.py` — Filters by `line.width >= wall_thickness_min`, standardizes direction (left-to-right), dedupes within tolerance using Euclidean distance
- **Raster wall extraction**: `app/services/raster_wall_extractor.py` — `extract_walls_from_raster()` converts PDF to PNG at 2x scale, sends to Gemini 2.5 Flash with structured prompt targeting structural walls; returns `WallDetectionResult` with `source="raster"`; requires `GOOGLE_API_KEY`
- **Gemini semantics**: `app/services/semantic_extractor.py` — `extract_semantics()` converts page to PNG via `page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))`; uses Gemini structured output with `SemanticResult` schema; returns empty `SemanticResult()` on any failure

### Model Contracts
- **Geometry**: `app/models/geometry.py` — `VectorLine` has `length()`, `is_horizontal(tolerance=0.1)`, `is_vertical()`; `ExtractionResult` has `get_bounding_box()`, `get_unique_widths()`
- **Semantic**: `app/models/semantic.py` — `RoomLabel`, `ScaleInfo`, `SemanticResult` — designed for Gemini JSON schema response
- **Spatial**: `app/models/spatial.py` — `Room` references walls by index; `SpatialGraph` is the assembled floorplan representation

## 6) Context Optimization (Claude-Specific)

1. **System prompt loading**: Core rules in system prompt, task details in user message
2. **XML structure**: Claude parses XML well — use task XML format from GSD-STYLE.md
3. **Conversation history**: Minimal history preferred; use STATE.md for continuity

### Example XML Format
```xml
<file path="app/services/wall_detector.py">
{relevant code section}
</file>

<task>
Add a configurable deduplication tolerance parameter to detect_walls()
</task>
```

## 7) Fast Verification Matrix
- If `pdf_extractor.py` changed -> run `pytest tests/test_pdf_extractor.py`
- If `wall_detector.py` changed -> run `pytest tests/test_wall_detector.py`
- If `raster_wall_extractor.py` changed -> run `pytest tests/test_raster_wall_extractor.py`
- If API/pipeline changed -> run `pytest tests/test_ingestion_pipeline.py`
- If semantic extraction changed -> run `pytest tests/test_semantic_extractor.py`
- Before declaring phase done -> run `pytest`

## 8) Token Guards
- Prefer grep/glob first; avoid full-file reads unless necessary
- Do not reload files already summarized unless behavior changed
- Keep one active objective at a time (current phase/task)
- After 3 failed attempts, write state and recommend `/pause`

## 9) Practical Codebase Constraints
- Preserve endpoints and response shape for `/api/v1/ingest`, `/health`, `/`
- Keep wall detection deterministic (thickness threshold + dedupe tolerance)
- Keep semantic extractor resilient when `GOOGLE_API_KEY` is absent
- Raster extraction requires `GOOGLE_API_KEY` (hard dependency)
- WallDetectionResult now includes `source` field (`"vector"` or `"raster"`)
- Avoid broad refactors outside current phase scope

## 10) Suggested Command Flow
- New work: `/progress` -> `/discuss-phase N` (optional) -> `/plan N`
- Build work: `/execute N`
- Prove work: `/verify N`
- If gaps found: `/execute N --gaps-only` then `/verify N`

## 11) Artifacts Mode

When artifacts are supported:

- ✅ Use for code generation that needs preview
- ✅ Use for documentation with formatting
- ❌ Avoid for small inline edits

---

## Appendix: Claude-Specific Code Patterns

### Key Function Signatures
```python
# app/services/ingestion_pipeline.py
def ingest_pdf(pdf_path: str) -> WallDetectionResult:
    """Extracts walls from PDF. Tries vector path first, falls back to raster via Gemini."""

# app/services/pdf_extractor.py
def extract_vectors(pdf_path: str, page_num: int = 0) -> ExtractionResult:
    """Extracts lines and rectangles from PDF vector graphics."""

def extract_summary(pdf_path: str, page_num: int = 0) -> dict:
    """Debug helper: returns line counts, bounding box, unique widths."""

# app/services/wall_detector.py
def detect_walls(extraction: ExtractionResult, wall_thickness_min: float = 1.5) -> WallDetectionResult:
    """Heuristic wall detection based on stroke thickness."""

# app/services/raster_wall_extractor.py
def extract_walls_from_raster(pdf_path: str, page_num: int = 0) -> WallDetectionResult:
    """Extract walls from raster/image PDF using Gemini 2.5 Flash vision.
    Raises RuntimeError if GOOGLE_API_KEY is missing.
    Returns WallDetectionResult with source='raster'.
    """

# app/services/semantic_extractor.py
def extract_semantics(pdf_path: str, page_num: int = 0) -> SemanticResult:
    """Vision-based extraction; returns empty result on failure."""
```

### Common Pitfalls
1. **Scanned PDFs**: Pipeline now automatically falls back to raster extraction via Gemini
2. **Missing API Key for Raster**: `raster_wall_extractor` requires `GOOGLE_API_KEY` — raises RuntimeError if missing
3. **Missing API Key for Semantic**: `semantic_extractor` logs warning and returns empty result — do not fail the pipeline
4. **Coordinate System**: PDF points (1/72 inch), origin at top-left; Y increases downward
5. **Raster Coordinates**: Gemini returns pixel coords at 2x scale; divided by 2.0 to get PDF points
6. **Deduplication**: Wall detector uses 2-point tolerance — modifying this affects wall count
7. **Source Field**: `WallDetectionResult.source` is `"vector"` or `"raster"` — use for debugging/provenance

### Quick Debugging Queries
```bash
# Check if PDF has vectors
python -c "from app.services.pdf_extractor import extract_summary; print(extract_summary('sample_pdfs/test.pdf'))"

# Run specific test with verbose output
pytest tests/test_wall_detector.py -v --tb=short
```

### Anti-Patterns (Claude-Specific)

❌ **Using max effort for everything** — Slow and expensive  
❌ **Skipping verification** — Thinking mode doesn't guarantee correctness  
❌ **Depending on artifacts** — Not all Claude interfaces support them  
❌ **Long conversation history** — Use STATE.md instead of relying on context  
❌ **Ignoring workflow files** — `.agent/workflows/*.md` are MANDATORY  
❌ **More than 3 tasks per plan** — Violates GSD atomicity  

### Checkpoint Protocol (Critical)

When encountering `type="checkpoint:*"` in tasks:

**STOP immediately.** Do not continue to next task.

Return this EXACT structure:

```markdown
## CHECKPOINT REACHED

**Type:** [human-verify | decision | human-action]
**Plan:** {phase}-{plan}
**Progress:** {completed}/{total} tasks complete

### Completed Tasks
| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | {task name} | {hash} | {files} |

### Current Task
**Task {N}:** {task name}
**Status:** {blocked | awaiting verification | awaiting decision}
**Blocked by:** {specific blocker}

### Checkpoint Details
{Checkpoint-specific content}

### Awaiting
{What user needs to do/provide}
```
