# AGENTS.md

Token-efficient playbook for any LLM agent working this repo with GSD.

## 1) Rule Priority (always)
- Canonical rules: `PROJECT_RULES.md`
- Writing/style conventions: `GSD-STYLE.md`
- Command behavior: `.agent/workflows/*.md`

If guidance conflicts, follow that order.

## 2) GSD Loop (short form)
- `SPEC -> PLAN -> EXECUTE -> VERIFY -> COMMIT`
- Planning Lock: no implementation before `.gsd/SPEC.md` is `FINALIZED`
- Verification is empirical only (tests/output), never "should work"
- One task = one commit

## 3) 30-second Startup Checklist
- Check current state first: `.gsd/STATE.md`, `.gsd/ROADMAP.md`
- If project is brownfield and unmapped, run `/map` before heavy planning
- Work one phase at a time: `/plan N`, then `/execute N`, then `/verify N`
- After major work blocks, update state snapshot in `.gsd/STATE.md`

## 4) Token Budget Discipline
- Search first, then targeted read (do not read everything by default)
- Reuse summaries; avoid re-reading files already understood
- Keep plan tasks atomic (2-3 tasks per PLAN)
- Use fresh context per plan/wave; avoid long monolithic sessions
- After 3 failed attempts on one approach: dump state, switch approach or `/pause`

## 5) Repo Map (what matters most)

### Application Entry Points
- **Flask app entry**: `app/main.py` — Creates Flask app, registers blueprints, configures CORS, defines `/health` and `/` endpoints
- **API routes**: `app/api/routes.py` — Blueprint with `POST /api/v1/ingest` (main ingestion), `GET /api/v1/pdf/status/<id>` (placeholder)

### Core Services (Business Logic)
- **Ingestion orchestration**: `app/services/ingestion_pipeline.py` — `ingest_pdf()` coordinates extraction → wall detection; falls back to `extract_walls_from_raster()` when no vectors found
- **PDF vector extraction**: `app/services/pdf_extractor.py` — `extract_vectors()` uses PyMuPDF to parse line segments (`"l"` items) and rectangles (`"re"` items); returns `ExtractionResult`
- **Wall heuristics**: `app/services/wall_detector.py` — `detect_walls()` filters lines by `width >= 1.5` (configurable), deduplicates within 2pt tolerance, returns `WallDetectionResult`
- **Raster wall extraction**: `app/services/raster_wall_extractor.py` — `extract_walls_from_raster()` converts PDF to PNG at 2x scale, sends to Gemini 2.5 Flash with structured prompt, returns `WallDetectionResult` with `source="raster"`; requires `GOOGLE_API_KEY`
- **Semantic extraction (Gemini)**: `app/services/semantic_extractor.py` — `extract_semantics()` rasterizes PDF to PNG, calls Gemini-2.5-flash for room labels/scale; graceful fallback when `GOOGLE_API_KEY` is absent

### Data Models (Pydantic/SQLModel)
- **Geometry models**: `app/models/geometry.py` — `VectorLine` (with `is_horizontal()`, `is_vertical()`, `length()`), `ExtractionResult`, `WallSegment`, `WallDetectionResult` (now with `source` field: `"vector"` or `"raster"`)
- **Semantic models**: `app/models/semantic.py` — `RoomLabel`, `ScaleInfo`, `SemanticResult` (used by Gemini structured output)
- **Spatial model**: `app/models/spatial.py` — `Room` (boundary wall indices), `SpatialGraph` (complete floorplan representation)
- **DB models**: `app/models/database.py` — SQLModel tables: `Project`, `Floorplan`, `MaterialPricing`, `GeneratedBOM` (Supabase PostgreSQL)

### Configuration
- **Settings**: `app/core/config.py` — Pydantic-settings with `PROJECT_NAME`, `SUPABASE_*`, `GOOGLE_API_KEY`; loads from `.env`

### Tests
- **PDF extraction**: `tests/test_pdf_extractor.py`
- **Wall detection**: `tests/test_wall_detector.py`
- **Raster wall extraction**: `tests/test_raster_wall_extractor.py` — 42 tests covering unit and integration scenarios
- **Pipeline/API**: `tests/test_ingestion_pipeline.py` — Tests `/health`, `/api/v1/ingest`, error cases
- **Semantic extraction**: `tests/test_semantic_extractor.py`

## 6) Fast Test Routing (verify only what changed)
- PDF extraction changes -> `pytest tests/test_pdf_extractor.py`
- Wall detection changes -> `pytest tests/test_wall_detector.py`
- Raster wall extraction changes -> `pytest tests/test_raster_wall_extractor.py`
- Pipeline/API changes -> `pytest tests/test_ingestion_pipeline.py`
- Gemini semantic changes -> `pytest tests/test_semantic_extractor.py`
- Full pass -> `pytest`

---

## 7) GSD Spec-Driven Development Workflow (CORE)

This codebase follows **GSD (Get Shit Done) Spec-Driven Development**. The workflows and skills in `.agent/` are **NOT optional** — they define how work is done.

### 7.1 Core Philosophy

**Plans Are Prompts** — PLAN.md files are executable instructions, not documentation. When planning a phase, you are writing the prompt that will execute it.

**Solo Developer + AI** — Plan for ONE person (the user) and ONE implementer (the AI). No teams, ceremonies, or coordination overhead.

**Ship Fast** — Plan → Execute → Ship → Learn → Repeat. No enterprise process.

### 7.2 Quality Degradation Curve

| Context Usage | Quality | State |
|---------------|---------|-------|
| 0-30% | PEAK | Thorough, comprehensive |
| 30-50% | GOOD | Confident, solid work |
| 50-70% | DEGRADING | Efficiency mode begins |
| 70%+ | POOR | Rushed, minimal |

**Rule:** Plans should complete within ~50% context. Each plan: **2-3 tasks max**.

### 7.3 Workflow Commands (MANDATORY)

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/new-project` | Initialize project with SPEC → ROADMAP | Starting new work |
| `/map` | Analyze codebase → ARCHITECTURE.md | Brownfield projects before planning |
| `/plan N` | Create executable plans for phase N | SPEC finalized, ready to implement |
| `/execute N` | Execute all plans in phase N | Plans exist, ready to build |
| `/verify N` | Validate work with empirical proof | After execution, before next phase |
| `/debug` | Systematic debugging with state | When tasks fail verification |
| `/progress` | Show current position and next steps | Anytime you need orientation |
| `/pause` | Save state for session handoff | After 3 failures, context heavy, ending session |
| `/resume` | Restore context from previous session | Starting new session |

### 7.4 Execution Rules (Non-Negotiable)

**Planning Lock:** No code until `SPEC.md` is `FINALIZED`.

**Atomic Commits:** One task = one commit. Format: `type(scope): description`

**Verification Required:** Every change needs proof (test output, curl response, screenshot).

**3-Strike Rule:** After 3 failed debugging attempts → dump state → `/pause` → fresh session.

### 7.5 Skills Reference (MANDATORY)

All skills are in `.agent/skills/` and define detailed methodologies:

| Skill | Purpose |
|-------|---------|
| `planner` | Plan creation with goal-backward methodology |
| `plan-checker` | Validates plans before execution |
| `executor` | Task execution with deviation handling |
| `verifier` | Empirical validation with stub detection |
| `debugger` | Hypothesis-driven debugging |
| `codebase-mapper` | Brownfield codebase analysis |
| `context-health-monitor` | 3-strike rule enforcement |
| `empirical-validation` | Evidence requirements |
| `token-budget` | Context efficiency |
| `context-compressor` | State summarization |
| `context-fetch` | Targeted file loading |

### 7.6 Deviation Rules (During Execution)

When executing, you WILL discover work not in the plan. Apply these rules:

| Rule | Trigger | Action |
|------|---------|--------|
| **Rule 1** | Code doesn't work (bugs, errors) | Auto-fix inline, track in Summary |
| **Rule 2** | Missing critical functionality (validation, auth) | Auto-add, track in Summary |
| **Rule 3** | Blocking issues (missing deps, broken imports) | Auto-fix, track in Summary |
| **Rule 4** | Architectural changes (new tables, breaking API changes) | STOP → checkpoint → user decision |

**Priority:** Rule 4 > Rules 1-3. If unsure, apply Rule 4.

---

## 8) Practical Defaults for This Codebase
- Keep API behavior stable (`/api/v1/ingest`, `/health`, `/`)
- Preserve graceful degradation in semantic extraction when `GOOGLE_API_KEY` is missing
- Keep wall detection deterministic (thickness filter + dedupe tolerance)
- Prefer focused tests over full-suite runs during iteration; run full suite before final verification

---

## Appendix A: Key Implementation Details

### Data Flow
```
PDF Upload → /api/v1/ingest → extract_vectors() → [has vectors?] → detect_walls() → WallDetectionResult → JSON Response
                                    ↓
                              [no vectors]
                                    ↓
                     extract_walls_from_raster() → Gemini 2.5 Flash → WallDetectionResult → JSON Response
                                    ↓
                          extract_semantics() (optional, when API key present)
                                    ↓
                          SemanticResult (rooms, scale)
```

### Critical Constants
| File | Constant | Value | Purpose |
|------|----------|-------|---------|
| `wall_detector.py` | `wall_thickness_min` | `1.5` | Minimum stroke width to qualify as structural wall |
| `wall_detector.py` | `tolerance` | `2.0` | Deduplication tolerance in PDF points |
| `pdf_extractor.py` | DPI scaling | `Matrix(2.0, 2.0)` | ~144 DPI for semantic rasterization |
| `raster_wall_extractor.py` | DPI scaling | `Matrix(2.0, 2.0)` | 2x scale for Gemini vision input |
| `raster_wall_extractor.py` | Coordinate divisor | `2.0` | Convert pixel coords back to PDF points |

### Response Contracts
**`POST /api/v1/ingest` success (200) - Vector PDF:**
```json
{
  "wall_segments": [
    {"x1": 100.0, "y1": 50.0, "x2": 300.0, "y2": 50.0, "length_pts": 200.0, "thickness": 2.0}
  ],
  "total_wall_count": 1,
  "total_linear_pts": 200.0,
  "source": "vector"
}
```

**`POST /api/v1/ingest` success (200) - Raster PDF:**
```json
{
  "wall_segments": [
    {"x1": 50.0, "y1": 50.0, "x2": 250.0, "y2": 50.0, "length_pts": 200.0, "thickness": 4.0}
  ],
  "total_wall_count": 1,
  "total_linear_pts": 200.0,
  "source": "raster"
}
```

**`POST /api/v1/ingest` error - missing API key for raster (500):**
```json
{"error": "Raster processing requires GOOGLE_API_KEY"}
```

---

## Appendix B: Model-Agnostic LLM Guidelines

All LLMs working this codebase MUST follow these guidelines, regardless of provider.

### B.1 Reasoning Effort / Model Selection

Match reasoning effort to task complexity:

| Task Type | Effort Level |
|-----------|--------------|
| Architecture planning, complex debugging, security analysis | High/Max reasoning |
| Standard implementation, refactoring | Medium reasoning (default) |
| Simple edits, formatting, comments | Low reasoning |
| Quick iterations, typo fixes | Low/Fast model |

### B.2 Context Window Management

Regardless of context window size:

1. **Search-first discipline** — Never load full files without searching first
2. **Quality threshold at 50%** — Context quality degrades past this point
3. **Batch strategically** — Group related files, but don't load entire codebase
4. **Use clear separators** — XML tags or markdown headers to separate file contents

### B.3 Structured Prompting

Use explicit structure for complex tasks:

```markdown
## Task
{clear task description}

## Context
{relevant code snippets}

## Expected Output
{what you need back}

## Constraints
{limitations or requirements}
```

### B.4 Tool Use Patterns

When tool/function calling is available:

| Use Case | Example |
|----------|---------|
| Verification commands | Run tests, check outputs |
| File operations | Read/write specific files |
| External service checks | API health, documentation lookup |

### B.5 Anti-Patterns (All Models)

❌ **Using max effort for everything** — Slow and expensive  
❌ **Loading entire codebase** — Even with large context, quality degrades  
❌ **Skipping verification** — Reasoning mode doesn't guarantee correctness  
❌ **Ignoring context thresholds** — 50% is the quality boundary  
❌ **Complex nested prompts** — Keep structure flat and clear  
❌ **Skipping STATE.md** — Context window size doesn't replace persistent state  
❌ **Treating workflows as optional** — `.agent/workflows/` are MANDATORY  
❌ **More than 3 tasks per plan** — Violates atomicity principle  

### B.6 Model-Specific Adapters

For provider-specific enhancements, see:
- **Claude**: `adapters/CLAUDE.md` — Extended thinking, artifacts mode
- **Gemini**: `adapters/GEMINI.md` — Flash vs Pro selection, grounding
- **GPT/OSS**: `adapters/GPT_OSS.md` — Function calling, local deployment

These adapters are optional but recommended for optimal performance.

---

## Appendix C: Task XML Structure (Required)

All tasks in PLAN.md files MUST use this XML structure:

```xml
<task type="auto">
  <name>{Clear task name}</name>
  <files>{exact/file/paths.ext}</files>
  <action>
    {Specific implementation instructions}
    AVOID: {common mistake} because {reason}
  </action>
  <verify>{executable command or check}</verify>
  <done>{measurable acceptance criteria}</done>
</task>
```

### Task Types

| Type | Use For | Autonomy |
|------|---------|----------|
| `auto` | Everything AI can do independently | Fully autonomous |
| `checkpoint:human-verify` | Visual/functional verification | Pauses for user |
| `checkpoint:decision` | Implementation choices | Pauses for user |
| `checkpoint:human-action` | Truly unavoidable manual steps | Pauses for user |

**Automation-first rule:** If AI CAN do it via CLI/API, AI MUST do it.
