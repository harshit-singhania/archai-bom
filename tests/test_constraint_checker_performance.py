"""Performance regression tests for constraint_checker.validate_layout.

Verifies that indexed room and fixture overlap checks (STRtree-backed)
complete within a fixed timing envelope under large synthetic layouts.
These tests guard against accidental reintroduction of O(n^2) polygon
intersection behavior.
"""

import time

import pytest

from app.models.layout import GeneratedLayout
from app.services.constraint_checker import validate_layout


# ---------------------------------------------------------------------------
# Synthetic layout builders
# ---------------------------------------------------------------------------

def _make_grid_rooms(n_cols: int, n_rows: int, room_size_mm: float = 5000.0) -> list[dict]:
    """
    Build n_cols * n_rows non-overlapping rectangular rooms on a regular grid.

    Each room is a closed polygon with 1mm padding to avoid shared edges
    triggering the overlap tolerance.
    """
    pad = 1.0
    rooms = []
    for row in range(n_rows):
        for col in range(n_cols):
            x0 = col * room_size_mm + pad
            y0 = row * room_size_mm + pad
            x1 = x0 + room_size_mm - 2 * pad
            y1 = y0 + room_size_mm - 2 * pad
            rooms.append(
                {
                    "name": f"Room_{row}_{col}",
                    "room_type": "operatory",
                    "boundary": [
                        (x0, y0),
                        (x1, y0),
                        (x1, y1),
                        (x0, y1),
                        (x0, y0),
                    ],
                    "area_sqm": (room_size_mm / 1000.0) ** 2,
                }
            )
    return rooms


def _make_grid_fixtures(rooms: list[dict], fixtures_per_room: int, fixture_size_mm: float = 400.0) -> list[dict]:
    """
    Place *fixtures_per_room* non-overlapping fixtures inside each room.

    Fixtures are placed in a row along the x-axis, padded from the room corner.
    """
    fixtures = []
    fx_id = 0
    spacing = fixture_size_mm + 10.0
    for room in rooms:
        boundary = room["boundary"]
        origin_x = boundary[0][0] + fixture_size_mm
        origin_y = boundary[0][1] + fixture_size_mm
        for k in range(fixtures_per_room):
            cx = origin_x + k * spacing
            cy = origin_y
            fixtures.append(
                {
                    "id": f"fx_{fx_id}",
                    "room_name": room["name"],
                    "fixture_type": "desk",
                    "center_x": cx,
                    "center_y": cy,
                    "width_mm": fixture_size_mm,
                    "depth_mm": fixture_size_mm,
                    "rotation_deg": 0.0,
                }
            )
            fx_id += 1
    return fixtures


def _build_large_layout(n_rooms: int, fixtures_per_room: int = 5) -> GeneratedLayout:
    """
    Build a synthetic layout with *n_rooms* non-overlapping rooms, each
    containing *fixtures_per_room* non-overlapping fixtures.

    Grid dimensions: nearest square root to keep the layout roughly square.
    """
    import math

    n_cols = math.ceil(math.sqrt(n_rooms))
    n_rows = math.ceil(n_rooms / n_cols)
    room_size_mm = 5000.0

    rooms = _make_grid_rooms(n_cols, n_rows, room_size_mm)[:n_rooms]
    fixtures = _make_grid_fixtures(rooms, fixtures_per_room)

    total_width = n_cols * room_size_mm
    total_height = n_rows * room_size_mm

    perimeter_walls = [
        {"id": "pw_top", "x1": 0.0, "y1": 0.0, "x2": total_width, "y2": 0.0, "thickness_mm": 200.0},
        {"id": "pw_right", "x1": total_width, "y1": 0.0, "x2": total_width, "y2": total_height, "thickness_mm": 200.0},
        {"id": "pw_bottom", "x1": total_width, "y1": total_height, "x2": 0.0, "y2": total_height, "thickness_mm": 200.0},
        {"id": "pw_left", "x1": 0.0, "y1": total_height, "x2": 0.0, "y2": 0.0, "thickness_mm": 200.0},
    ]

    return GeneratedLayout(
        rooms=rooms,
        interior_walls=[],
        doors=[],
        fixtures=fixtures,
        grid_size_mm=50,
        prompt="performance_test",
        perimeter_walls=perimeter_walls,
        page_dimensions_mm=(total_width, total_height),
    )


# ---------------------------------------------------------------------------
# Performance benchmarks
# ---------------------------------------------------------------------------

class TestConstraintCheckerPerformance:
    """Performance regression suite for validate_layout().

    Timing envelopes are conservative and reflect expected wall-clock budget
    on a single-core reference run. The intent is to catch severe regressions
    (e.g., reintroducing O(n^2) loops), not to enforce microsecond precision.
    """

    def test_large_room_layout_completes_within_time_budget(self):
        """100 non-overlapping rooms should validate in under 5 seconds."""
        layout = _build_large_layout(n_rooms=100, fixtures_per_room=0)

        start = time.monotonic()
        result = validate_layout(layout)
        elapsed = time.monotonic() - start

        assert result.passed is True, (
            f"Expected valid layout; violations: {[v.description for v in result.violations]}"
        )
        assert elapsed < 5.0, (
            f"validate_layout took {elapsed:.2f}s for 100 rooms — possible O(n^2) regression"
        )

    def test_large_fixture_layout_completes_within_time_budget(self):
        """20 rooms with 20 fixtures each (400 fixtures total) should validate in under 5 seconds."""
        layout = _build_large_layout(n_rooms=20, fixtures_per_room=20)

        start = time.monotonic()
        result = validate_layout(layout)
        elapsed = time.monotonic() - start

        # Warnings expected only if fixture layout exceeds room area check
        error_violations = [v for v in result.violations if v.severity == "error"]
        assert error_violations == [], (
            f"Unexpected errors in large fixture layout: {[v.description for v in error_violations]}"
        )
        assert elapsed < 5.0, (
            f"validate_layout took {elapsed:.2f}s for 400 fixtures — possible O(n^2) regression"
        )

    def test_combined_high_entity_layout_completes_within_time_budget(self):
        """50 rooms with 10 fixtures each (500 fixtures) should validate in under 10 seconds."""
        layout = _build_large_layout(n_rooms=50, fixtures_per_room=10)

        start = time.monotonic()
        result = validate_layout(layout)
        elapsed = time.monotonic() - start

        error_violations = [v for v in result.violations if v.severity == "error"]
        assert error_violations == [], (
            f"Unexpected errors: {[v.description for v in error_violations]}"
        )
        assert elapsed < 10.0, (
            f"validate_layout took {elapsed:.2f}s for 500 entities — possible O(n^2) regression"
        )

    def test_single_room_is_instant(self):
        """Single room with no fixtures should be validated near-instantly."""
        layout = _build_large_layout(n_rooms=1, fixtures_per_room=0)

        start = time.monotonic()
        result = validate_layout(layout)
        elapsed = time.monotonic() - start

        assert result.passed is True
        assert elapsed < 1.0, f"Single room took {elapsed:.2f}s — unexpected slowdown"

    def test_correctness_preserved_at_scale(self):
        """STRtree-indexed path must still detect overlapping rooms in a large layout."""
        layout = _build_large_layout(n_rooms=20, fixtures_per_room=0)

        # Manually corrupt one room boundary to overlap with its neighbour
        # Room_0_0 occupies roughly (1, 1) to (4999, 4999).
        # Inject a room that overlaps it significantly.
        overlapping_room = {
            "name": "Intruder",
            "room_type": "operatory",
            "boundary": [
                (500.0, 500.0),
                (3000.0, 500.0),
                (3000.0, 3000.0),
                (500.0, 3000.0),
                (500.0, 500.0),
            ],
            "area_sqm": 6.25,
        }
        payload = layout.model_dump()
        payload["rooms"].append(overlapping_room)
        modified_layout = GeneratedLayout(**payload)

        result = validate_layout(modified_layout)

        from app.models.constraints import ConstraintViolationType

        assert any(
            v.type == ConstraintViolationType.ROOM_OVERLAP
            and "Intruder" in v.affected_elements
            for v in result.violations
        ), "STRtree path failed to detect expected room overlap"
