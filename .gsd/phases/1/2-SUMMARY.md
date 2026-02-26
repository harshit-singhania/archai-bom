# Plan 1.2: Layer Filtering & Wall Detection - SUMMARY

## Objective Reached

Successfully took raw vector lines from Plan 1.1 and classified structural walls by identifying thick line strokes and disregarding annotation/dimension lines. Implemented a full ingestion pipeline endpoint for end-to-end functionality.

## Deliverables

1. **Geometry Models Updated**: Added `WallSegment` and `WallDetectionResult` to `app/models/geometry.py`.
2. **Wall Detection Service**: Created `app/services/wall_detector.py` implementing heuristic filtering (thickness >= 1.5) and deduplication (2.0 pt tolerance).
3. **Ingestion Pipeline**: Created `app/services/ingestion_pipeline.py` to chain extraction and detection.
4. **API Endpoint**: Added `POST /api/v1/ingest` in `app/api/routes.py` accepting PDF files and returning wall geometry JSON.
5. **Testing**: Implemented robust unit tests for `wall_detector.py` and integration tests for `ingestion_pipeline.py` (tested with `test_floorplan.pdf`).

## Verification

- Unit and Integration tests passing.
- Duplicate segments correctly identified and merged.
- Non-vector PDFs explicitly handled and rejected (HTTP 400).
