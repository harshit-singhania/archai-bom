"""Grid snapping utilities for generated layouts.

Snapping is performed per coordinate on a fixed construction grid (default 50mm).
If two elements share an identical endpoint before snapping, they stay connected after
snapping because the same input coordinate maps to the same grid point. Elements that
are close-but-not-identical may collapse onto a shared coordinate after snapping.
"""

import math

from app.models.layout import GeneratedLayout


def snap_to_grid(value: float, grid_mm: int = 50) -> float:
    """Round a value to the nearest grid increment."""

    if grid_mm <= 0:
        raise ValueError("grid_mm must be greater than 0")

    ratio = value / grid_mm
    if ratio >= 0:
        snapped_ratio = math.floor(ratio + 0.5)
    else:
        snapped_ratio = math.ceil(ratio - 0.5)
    return float(snapped_ratio * grid_mm)


def _shoelace_area_sqm(boundary: list[tuple[float, float]]) -> float:
    """Calculate polygon area from boundary vertices using shoelace formula."""

    area_twice = 0.0
    for idx in range(len(boundary) - 1):
        x1, y1 = boundary[idx]
        x2, y2 = boundary[idx + 1]
        area_twice += (x1 * y2) - (x2 * y1)

    area_mm2 = abs(area_twice) / 2.0
    return area_mm2 / 1_000_000.0


def snap_layout_to_grid(layout: GeneratedLayout, grid_mm: int = 50) -> GeneratedLayout:
    """Return a snapped copy of a GeneratedLayout without mutating the original."""

    layout_copy = layout.model_copy(deep=True)

    for wall in layout_copy.interior_walls:
        wall.x1 = snap_to_grid(wall.x1, grid_mm)
        wall.y1 = snap_to_grid(wall.y1, grid_mm)
        wall.x2 = snap_to_grid(wall.x2, grid_mm)
        wall.y2 = snap_to_grid(wall.y2, grid_mm)

    for fixture in layout_copy.fixtures:
        fixture.center_x = snap_to_grid(fixture.center_x, grid_mm)
        fixture.center_y = snap_to_grid(fixture.center_y, grid_mm)
        fixture.width_mm = snap_to_grid(fixture.width_mm, grid_mm)
        fixture.depth_mm = snap_to_grid(fixture.depth_mm, grid_mm)

    for room in layout_copy.rooms:
        snapped_boundary: list[tuple[float, float]] = []
        for x, y in room.boundary:
            snapped_boundary.append(
                (snap_to_grid(x, grid_mm), snap_to_grid(y, grid_mm))
            )

        room.boundary = snapped_boundary
        room.area_sqm = _shoelace_area_sqm(snapped_boundary)

    snapped_perimeter_walls = []
    for wall in layout_copy.perimeter_walls:
        wall_data = dict(wall)
        for key in ("x1", "y1", "x2", "y2", "thickness_mm"):
            if isinstance(wall_data.get(key), (int, float)):
                wall_data[key] = snap_to_grid(float(wall_data[key]), grid_mm)
        snapped_perimeter_walls.append(wall_data)
    layout_copy.perimeter_walls = snapped_perimeter_walls

    layout_copy.page_dimensions_mm = (
        snap_to_grid(layout_copy.page_dimensions_mm[0], grid_mm),
        snap_to_grid(layout_copy.page_dimensions_mm[1], grid_mm),
    )
    layout_copy.grid_size_mm = grid_mm

    return layout_copy
