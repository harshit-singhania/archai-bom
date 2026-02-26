"""Tests for Shapely-based layout constraint validation."""

from app.models.constraints import ConstraintViolationType
from app.models.layout import GeneratedLayout
from app.services.constraint_checker import validate_layout


def _base_layout_payload() -> dict:
    return {
        "rooms": [
            {
                "name": "Room A",
                "room_type": "operatory",
                "boundary": [
                    (0.0, 0.0),
                    (5000.0, 0.0),
                    (5000.0, 4000.0),
                    (0.0, 4000.0),
                    (0.0, 0.0),
                ],
                "area_sqm": 20.0,
            },
            {
                "name": "Room B",
                "room_type": "reception",
                "boundary": [
                    (5000.0, 0.0),
                    (10000.0, 0.0),
                    (10000.0, 4000.0),
                    (5000.0, 4000.0),
                    (5000.0, 0.0),
                ],
                "area_sqm": 20.0,
            },
        ],
        "interior_walls": [
            {
                "id": "iw_split",
                "x1": 5000.0,
                "y1": 0.0,
                "x2": 5000.0,
                "y2": 4000.0,
                "thickness_mm": 100.0,
                "material": "drywall",
            }
        ],
        "doors": [],
        "fixtures": [],
        "grid_size_mm": 50,
        "prompt": "test",
        "perimeter_walls": [
            {
                "id": "perimeter_top",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 10000.0,
                "y2": 0.0,
                "thickness_mm": 200.0,
            },
            {
                "id": "perimeter_right",
                "x1": 10000.0,
                "y1": 0.0,
                "x2": 10000.0,
                "y2": 8000.0,
                "thickness_mm": 200.0,
            },
            {
                "id": "perimeter_bottom",
                "x1": 10000.0,
                "y1": 8000.0,
                "x2": 0.0,
                "y2": 8000.0,
                "thickness_mm": 200.0,
            },
            {
                "id": "perimeter_left",
                "x1": 0.0,
                "y1": 8000.0,
                "x2": 0.0,
                "y2": 0.0,
                "thickness_mm": 200.0,
            },
        ],
        "page_dimensions_mm": (10000.0, 8000.0),
    }


def test_validate_layout_valid_two_rooms_passes():
    """Two non-overlapping rectangular rooms should pass."""

    layout = GeneratedLayout(**_base_layout_payload())
    result = validate_layout(layout)

    assert result.passed is True
    assert result.summary == "0 errors, 0 warnings"


def test_validate_layout_detects_room_overlap_error():
    """Overlapping rooms should trigger ROOM_OVERLAP error."""

    payload = _base_layout_payload()
    payload["rooms"][1]["boundary"] = [
        (4000.0, 0.0),
        (9000.0, 0.0),
        (9000.0, 4000.0),
        (4000.0, 4000.0),
        (4000.0, 0.0),
    ]

    result = validate_layout(GeneratedLayout(**payload))

    assert result.passed is False
    assert any(
        v.type == ConstraintViolationType.ROOM_OVERLAP for v in result.violations
    )


def test_validate_layout_detects_narrow_corridor_error():
    """A 600mm corridor should fail minimum width validation."""

    payload = _base_layout_payload()
    payload["rooms"] = [
        {
            "name": "Corridor",
            "room_type": "corridor",
            "boundary": [
                (0.0, 0.0),
                (600.0, 0.0),
                (600.0, 6000.0),
                (0.0, 6000.0),
                (0.0, 0.0),
            ],
            "area_sqm": 3.6,
        }
    ]

    result = validate_layout(GeneratedLayout(**payload))

    assert result.passed is False
    assert any(
        v.type == ConstraintViolationType.CORRIDOR_TOO_NARROW for v in result.violations
    )


def test_validate_layout_detects_door_swing_blocked_error():
    """Door swing intersecting a wall should trigger DOOR_SWING_BLOCKED."""

    payload = _base_layout_payload()
    payload["rooms"] = [
        {
            "name": "Clinic",
            "room_type": "operatory",
            "boundary": [
                (0.0, 0.0),
                (6000.0, 0.0),
                (6000.0, 4000.0),
                (0.0, 4000.0),
                (0.0, 0.0),
            ],
            "area_sqm": 24.0,
        }
    ]
    payload["interior_walls"] = [
        {
            "id": "iw_host",
            "x1": 0.0,
            "y1": 0.0,
            "x2": 2500.0,
            "y2": 0.0,
            "thickness_mm": 100.0,
            "material": "drywall",
        },
        {
            "id": "iw_block",
            "x1": 1250.0,
            "y1": 100.0,
            "x2": 1250.0,
            "y2": 1400.0,
            "thickness_mm": 100.0,
            "material": "drywall",
        },
    ]
    payload["doors"] = [
        {
            "id": "d_1",
            "wall_id": "iw_host",
            "position_along_wall": 0.5,
            "width_mm": 900.0,
            "swing_direction": "left",
            "door_type": "single",
        }
    ]

    result = validate_layout(GeneratedLayout(**payload))

    assert result.passed is False
    assert any(
        v.type == ConstraintViolationType.DOOR_SWING_BLOCKED for v in result.violations
    )


def test_validate_layout_fixture_outside_room_is_warning():
    """Fixture center outside its room should produce warning."""

    payload = _base_layout_payload()
    payload["fixtures"] = [
        {
            "id": "f_1",
            "room_name": "Room A",
            "fixture_type": "desk",
            "center_x": 7000.0,
            "center_y": 2000.0,
            "width_mm": 800.0,
            "depth_mm": 600.0,
            "rotation_deg": 0.0,
        }
    ]

    result = validate_layout(GeneratedLayout(**payload))

    assert any(
        v.type == ConstraintViolationType.FIXTURE_OUTSIDE_ROOM
        and v.severity == "warning"
        for v in result.violations
    )


def test_validate_layout_warnings_do_not_fail_result():
    """Warnings alone should keep passed=True."""

    payload = _base_layout_payload()
    payload["fixtures"] = [
        {
            "id": "f_1",
            "room_name": "Room A",
            "fixture_type": "desk",
            "center_x": 7000.0,
            "center_y": 2000.0,
            "width_mm": 800.0,
            "depth_mm": 600.0,
            "rotation_deg": 0.0,
        }
    ]

    result = validate_layout(GeneratedLayout(**payload))

    assert result.passed is True
    assert result.summary == "0 errors, 1 warnings"


def test_validate_layout_empty_rooms_is_error():
    """No rooms should fail validation to trigger retry loop."""

    payload = _base_layout_payload()
    payload["rooms"] = []

    result = validate_layout(GeneratedLayout(**payload))

    assert result.passed is False
    assert any(
        v.type == ConstraintViolationType.ROOM_NOT_ENCLOSED and v.severity == "error"
        for v in result.violations
    )


def test_validate_layout_handles_zero_perimeter_thickness():
    """Zero-thickness perimeter wall metadata should not crash validation."""

    payload = _base_layout_payload()
    payload["perimeter_walls"][0]["thickness_mm"] = 0.0

    result = validate_layout(GeneratedLayout(**payload))

    assert result.passed is True
