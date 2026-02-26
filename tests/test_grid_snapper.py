"""Tests for layout construction grid snapping."""

from app.models.layout import GeneratedLayout
from app.services.grid_snapper import snap_layout_to_grid, snap_to_grid


def _layout_payload() -> dict:
    return {
        "rooms": [
            {
                "name": "Room A",
                "room_type": "operatory",
                "boundary": [
                    (0.0, 0.0),
                    (123.0, 0.0),
                    (123.0, 123.0),
                    (0.0, 123.0),
                    (0.0, 0.0),
                ],
                "area_sqm": 99.0,
            }
        ],
        "interior_walls": [
            {
                "id": "iw_1",
                "x1": 999.0,
                "y1": 2003.0,
                "x2": 1499.0,
                "y2": 2501.0,
                "thickness_mm": 101.0,
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
                "room_name": "Room A",
                "fixture_type": "desk",
                "center_x": 977.0,
                "center_y": 1049.0,
                "width_mm": 575.0,
                "depth_mm": 625.0,
                "rotation_deg": 0.0,
            }
        ],
        "grid_size_mm": 50,
        "prompt": "test layout",
        "perimeter_walls": [
            {
                "id": "perimeter_1",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 5010.0,
                "y2": 0.0,
                "thickness_mm": 201.0,
            }
        ],
        "page_dimensions_mm": (5010.0, 3995.0),
    }


def test_snap_to_grid_edge_cases():
    """snap_to_grid handles exact values, midpoints, and negatives."""

    assert snap_to_grid(1750.0, 50) == 1750.0
    assert snap_to_grid(1723.0, 50) == 1700.0
    assert snap_to_grid(1749.0, 50) == 1750.0
    assert snap_to_grid(1725.0, 50) == 1750.0
    assert snap_to_grid(-26.0, 50) == -50.0
    assert snap_to_grid(-25.0, 50) == -50.0
    assert snap_to_grid(-24.0, 50) == 0.0


def test_snap_layout_to_grid_outputs_multiples_of_50_and_recomputes_area():
    """All snapped coordinates are grid-aligned and room area is recomputed."""

    layout = GeneratedLayout(**_layout_payload())
    snapped = snap_layout_to_grid(layout, grid_mm=50)

    wall = snapped.interior_walls[0]
    assert wall.x1 % 50 == 0
    assert wall.y1 % 50 == 0
    assert wall.x2 % 50 == 0
    assert wall.y2 % 50 == 0

    fixture = snapped.fixtures[0]
    assert fixture.center_x % 50 == 0
    assert fixture.center_y % 50 == 0
    assert fixture.width_mm % 50 == 0
    assert fixture.depth_mm % 50 == 0

    for x, y in snapped.rooms[0].boundary:
        assert x % 50 == 0
        assert y % 50 == 0

    assert snapped.rooms[0].area_sqm == 0.01


def test_snap_layout_to_grid_does_not_mutate_original_layout():
    """snap_layout_to_grid returns a new layout and keeps source unchanged."""

    layout = GeneratedLayout(**_layout_payload())
    original_x1 = layout.interior_walls[0].x1
    original_area = layout.rooms[0].area_sqm

    snapped = snap_layout_to_grid(layout, grid_mm=50)

    assert layout.interior_walls[0].x1 == original_x1
    assert layout.rooms[0].area_sqm == original_area
    assert snapped is not layout
