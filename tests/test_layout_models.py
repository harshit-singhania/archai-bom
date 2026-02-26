"""Tests for layout DSL models."""

import pytest
from pydantic import ValidationError

from app.models.layout import GeneratedLayout


def _valid_layout_payload() -> dict:
    return {
        "rooms": [
            {
                "name": "Operatory 1",
                "room_type": "operatory",
                "boundary": [
                    (0.0, 0.0),
                    (3000.0, 0.0),
                    (3000.0, 3000.0),
                    (0.0, 3000.0),
                    (0.0, 0.0),
                ],
                "area_sqm": 9.0,
            }
        ],
        "interior_walls": [
            {
                "id": "iw_1",
                "x1": 3000.0,
                "y1": 0.0,
                "x2": 3000.0,
                "y2": 6000.0,
                "thickness_mm": 100.0,
                "material": "drywall",
            }
        ],
        "doors": [
            {
                "id": "d_1",
                "wall_id": "iw_1",
                "position_along_wall": 0.5,
                "width_mm": 900.0,
                "swing_direction": "left",
                "door_type": "single",
            }
        ],
        "fixtures": [
            {
                "id": "f_1",
                "room_name": "Operatory 1",
                "fixture_type": "dental_chair",
                "center_x": 1000.0,
                "center_y": 1200.0,
                "width_mm": 1000.0,
                "depth_mm": 1800.0,
                "rotation_deg": 90.0,
            }
        ],
        "grid_size_mm": 50,
        "prompt": "6 operatory dental clinic with reception",
        "perimeter_walls": [
            {
                "id": "perimeter_1",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 10000.0,
                "y2": 0.0,
                "thickness_mm": 200.0,
            }
        ],
        "page_dimensions_mm": (10000.0, 8000.0),
    }


def test_generated_layout_valid_construction():
    """GeneratedLayout accepts a valid full payload."""

    layout = GeneratedLayout(**_valid_layout_payload())

    assert len(layout.rooms) == 1
    assert len(layout.interior_walls) == 1
    assert len(layout.doors) == 1
    assert len(layout.fixtures) == 1
    assert layout.grid_size_mm == 50


def test_generated_layout_rejects_negative_dimensions():
    """Negative dimensions are rejected by validation."""

    payload = _valid_layout_payload()
    payload["fixtures"][0]["width_mm"] = -1000.0

    with pytest.raises(ValidationError):
        GeneratedLayout(**payload)


def test_generated_layout_to_json_round_trip():
    """to_json output can be deserialized back to equivalent model."""

    layout = GeneratedLayout(**_valid_layout_payload())

    serialized = layout.to_json()
    restored = GeneratedLayout.model_validate(serialized)

    assert restored == layout


def test_door_position_must_be_in_range():
    """Door.position_along_wall must be between 0.0 and 1.0."""

    payload = _valid_layout_payload()
    payload["doors"][0]["position_along_wall"] = 1.25

    with pytest.raises(ValidationError):
        GeneratedLayout(**payload)
