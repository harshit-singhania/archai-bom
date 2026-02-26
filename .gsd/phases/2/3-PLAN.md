---
phase: 2
plan: 3
wave: 3
---

# Plan 2.3: Self-Correcting Generation Loop & API Integration

## Objective

Wire the generation → snap → validate → feedback loop together into a single pipeline service, expose it via an API endpoint, and verify end-to-end. This is the capstone of Phase 2: a user sends a SpatialGraph + natural language prompt and receives a construction-ready, constraint-validated interior layout.

## Context

- .gsd/SPEC.md (max 3 iterations, deterministic fallback)
- .gsd/RESEARCH.md (Section 2: The Critic — LangGraph feedback loop)
- app/services/layout_generator.py (Plan 2.1 — raw generation)
- app/services/grid_snapper.py (Plan 2.2 — coordinate snapping)
- app/services/constraint_checker.py (Plan 2.2 — validation)
- app/models/layout.py (GeneratedLayout)
- app/models/constraints.py (ConstraintResult, ConstraintViolation)
- app/api/routes.py (existing Flask blueprint)

## Tasks

<task type="auto">
  <name>Build self-correcting generation pipeline</name>
  <files>
    app/services/generation_pipeline.py
    app/models/generation.py
    tests/test_generation_pipeline.py
  </files>
  <action>
    1. Create app/models/generation.py:

       - GenerationResult:
         - layout: GeneratedLayout | None (None if all iterations failed)
         - success: bool
         - iterations_used: int
         - constraint_history: list[ConstraintResult] (one per iteration)
         - error_message: str | None (if total failure)

    2. Create app/services/generation_pipeline.py:

       - generate_validated_layout(spatial_graph: SpatialGraph, prompt: str, max_iterations: int = 3) -> GenerationResult

       - Implementation (simple Python loop — no LangGraph dependency needed for MVP):

         for iteration in range(1, max_iterations + 1):
           1. If iteration == 1:
                Call generate_layout(spatial_graph, prompt)
              Else:
                Call generate_layout(spatial_graph, feedback_prompt)
                where feedback_prompt = original prompt + "\n\nPREVIOUS ATTEMPT FAILED VALIDATION. Fix these issues:\n" + formatted violation descriptions

           2. Call snap_layout_to_grid(layout)

           3. Call validate_layout(snapped_layout)

           4. If constraint_result.passed:
                Return GenerationResult(layout=snapped_layout, success=True, iterations_used=iteration, ...)

           5. If not passed:
                Build feedback_prompt from constraint violations
                Format each violation as: "- [ERROR] {description}" or "- [WARNING] {description}"
                Continue to next iteration

         If all iterations exhausted:
           Return GenerationResult(layout=last_snapped_layout, success=False, iterations_used=max_iterations, error_message="Layout failed validation after {max_iterations} attempts")

       - The feedback prompt construction is critical — it must give Gemini enough context to fix specific issues:
         - Include the original prompt
         - Include the specific violations with affected element IDs
         - Include the instruction: "Regenerate the layout fixing these constraint violations. Keep all valid elements unchanged where possible."

    3. tests/test_generation_pipeline.py:
       - Test happy path: mock generate_layout to return valid layout on first try → success=True, iterations_used=1
       - Test retry path: mock generate_layout to return invalid layout first, valid layout second → success=True, iterations_used=2
       - Test max iterations exceeded: mock generate_layout to always return invalid → success=False, iterations_used=3
       - Test feedback prompt construction: verify violation descriptions are included in retry prompt
       - Mock all external services (Gemini API, Shapely operations via constraint_checker)

    Do NOT:
    - Add LangGraph as a dependency — a simple for loop achieves the same result with zero overhead
    - Implement a deterministic fallback algorithm yet — return the last failed layout; the caller can decide what to do
    - Add async/concurrent generation — MVP is synchronous
    - Persist results to database — that's Phase 4
  </action>
  <verify>
    pytest tests/test_generation_pipeline.py -v
  </verify>
  <done>
    - generate_validated_layout() runs the generate → snap → validate loop
    - Constraint violations are fed back to Gemini as specific, actionable feedback
    - Stops early on success; stops at max_iterations on failure
    - GenerationResult includes full constraint history for debugging
    - All tests pass with mocked services
  </done>
</task>

<task type="auto">
  <name>API endpoint and end-to-end integration</name>
  <files>
    app/api/routes.py
    tests/test_generation_endpoint.py
  </files>
  <action>
    1. Update app/api/routes.py — add new endpoint to existing Flask blueprint:

       - POST /api/v1/generate
         - Request body (JSON):
           {
             "spatial_graph": { ... SpatialGraph JSON ... },
             "prompt": "6 operatory dental clinic with reception, waiting, sterilization"
           }
         - Validate request: spatial_graph must have walls, prompt must be non-empty string
         - Call generate_validated_layout(spatial_graph, prompt)
         - Response (JSON):
           {
             "success": true/false,
             "iterations_used": 1,
             "layout": { ... GeneratedLayout JSON ... },
             "constraint_result": { "passed": true, "violations": [] },
             "error_message": null
           }
         - Status codes:
           - 200: Generation succeeded (success=True)
           - 422: Generation failed validation after max retries (success=False, still returns last layout)
           - 400: Invalid request (missing spatial_graph or prompt)
           - 500: Gemini API failure or unexpected error

    2. tests/test_generation_endpoint.py:
       - Integration test with Flask test client
       - Mock Gemini API at the service level
       - Test successful generation: POST valid request → 200 + layout JSON
       - Test validation failure: POST → 422 + last layout + error_message
       - Test bad request: missing prompt → 400
       - Test empty spatial graph: no walls → 400

    Do NOT:
    - Add authentication or rate limiting
    - Stream responses or use WebSockets — MVP is synchronous request/response
    - Connect to the ingestion pipeline — Phase 2 endpoint takes SpatialGraph as input; the frontend (Phase 4) will chain ingestion → generation
  </action>
  <verify>
    pytest tests/test_generation_endpoint.py -v
    # Manual verification (requires running server + Gemini API key):
    # curl -X POST http://localhost:5000/api/v1/generate -H "Content-Type: application/json" -d '{"spatial_graph": {...}, "prompt": "open plan office with 4 meeting rooms"}'
  </verify>
  <done>
    - POST /api/v1/generate accepts SpatialGraph + prompt and returns GeneratedLayout
    - Response includes success flag, iteration count, constraint result, and layout JSON
    - Error responses have appropriate status codes and messages
    - Integration tests pass with mocked Gemini API
  </done>
</task>

<task type="checkpoint:human-verify">
  <name>End-to-end validation with sample spatial graph</name>
  <files>
    app/api/routes.py
    app/services/generation_pipeline.py
  </files>
  <action>
    Run full Phase 2 pipeline with a realistic spatial graph input:
    1. Create a sample SpatialGraph JSON inline — a ~200 sqm (20m x 10m) rectangular perimeter with 4 walls and 2 pre-labeled rooms ("Main Hall" and "Storage") from Phase 1 output format
    2. POST to /api/v1/generate with prompt: "Modern open-plan office with 4 private offices, 1 conference room, reception area, and pantry"
    3. Inspect returned GeneratedLayout JSON:
       - Are room boundaries reasonable?
       - Do interior walls subdivide the perimeter logically?
       - Are doors placed on walls?
       - Are fixtures appropriate for room types?
    4. Check constraint result — did it pass? If not, what violations?

    Print formatted summary:
    - Iterations used
    - Rooms generated (name, type, area)
    - Interior walls count
    - Doors count
    - Fixtures count
    - Constraint violations (if any)
  </action>
  <verify>
    # Construct sample SpatialGraph inline (20m x 10m rectangle = 200 sqm)
    curl -X POST http://localhost:5000/api/v1/generate \
      -H "Content-Type: application/json" \
      -d '{"spatial_graph": {"walls": [{"x1":0,"y1":0,"x2":20000,"y2":0,"length_pts":20000,"thickness":2.0},{"x1":20000,"y1":0,"x2":20000,"y2":10000,"length_pts":10000,"thickness":2.0},{"x1":20000,"y1":10000,"x2":0,"y2":10000,"length_pts":20000,"thickness":2.0},{"x1":0,"y1":10000,"x2":0,"y2":0,"length_pts":10000,"thickness":2.0}],"rooms":[{"name":"Main Hall","boundary_walls":[0,1,2,3],"area_sq_pts":200000000,"area_sq_ft":2152.78}],"scale_factor":1.0,"page_dimensions":[20000,10000]},"prompt":"Modern open-plan office with 4 private offices, 1 conference room, reception area, and pantry"}' \
      | python -m json.tool
  </verify>
  <done>
    User confirms:
    - Generated layout is spatially plausible for the given prompt
    - Room sizes are reasonable for their types
    - No major constraint violations
    - Phase 2 objective is met: SpatialGraph + prompt → validated interior layout
  </done>
</task>

## Success Criteria

- [ ] Self-correcting loop retries generation on constraint failures (up to 3 iterations)
- [ ] Constraint violations are formatted as actionable feedback for Gemini
- [ ] POST /api/v1/generate accepts SpatialGraph + prompt, returns validated layout
- [ ] Response includes success flag, iteration count, layout JSON, and constraint details
- [ ] End-to-end: realistic spatial graph + office prompt → plausible interior layout
- [ ] All automated tests pass
