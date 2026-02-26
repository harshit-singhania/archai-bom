"""Shapely-based spatial constraint checking for generated layouts."""

import math
from collections import defaultdict

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box

from app.models.constraints import (
    ConstraintResult,
    ConstraintViolation,
    ConstraintViolationType,
)
from app.models.layout import Door, GeneratedLayout, InteriorWall


def _as_float(value, default: float = 0.0) -> float:
    """Coerce arbitrary input to float with a fallback default."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _room_polygon(boundary: list[tuple[float, float]]) -> Polygon:
    """Create a Shapely polygon from room boundary vertices."""

    return Polygon(boundary)


def _wall_polygon(
    x1: float, y1: float, x2: float, y2: float, thickness_mm: float
) -> Polygon:
    """Create a buffered wall polygon from a centerline and thickness."""

    line = LineString([(x1, y1), (x2, y2)])
    if line.length == 0:
        return Polygon()
    return line.buffer(
        max(thickness_mm, 1.0) / 2.0, cap_style="flat", join_style="mitre"
    )


def _fixture_polygon(fixture) -> Polygon:
    """Create an oriented fixture rectangle polygon."""

    rect = box(
        -fixture.width_mm / 2.0,
        -fixture.depth_mm / 2.0,
        fixture.width_mm / 2.0,
        fixture.depth_mm / 2.0,
    )
    rotated = affinity.rotate(
        rect, fixture.rotation_deg, origin=(0, 0), use_radians=False
    )
    return affinity.translate(rotated, xoff=fixture.center_x, yoff=fixture.center_y)


def get_door_swing_arc(wall: InteriorWall, door: Door, segments: int = 32) -> Polygon:
    """Create a quarter-circle door swing sector polygon for hinged doors."""

    dx = wall.x2 - wall.x1
    dy = wall.y2 - wall.y1
    wall_length = math.hypot(dx, dy)
    if wall_length == 0:
        return Polygon()

    hinge_x = wall.x1 + (door.position_along_wall * dx)
    hinge_y = wall.y1 + (door.position_along_wall * dy)
    radius = door.width_mm
    wall_angle = math.atan2(dy, dx)
    end_angle = wall_angle + (math.pi / 2.0)
    if door.swing_direction == "right":
        end_angle = wall_angle - (math.pi / 2.0)

    points = [(hinge_x, hinge_y)]
    for step in range(segments + 1):
        t = step / segments
        angle = wall_angle + ((end_angle - wall_angle) * t)
        points.append(
            (hinge_x + radius * math.cos(angle), hinge_y + radius * math.sin(angle))
        )
    points.append((hinge_x, hinge_y))

    return Polygon(points)


def _build_wall_index(layout: GeneratedLayout) -> dict[str, InteriorWall]:
    """Build a unified wall id index from interior and perimeter walls."""

    wall_index: dict[str, InteriorWall] = {}
    for wall in layout.interior_walls:
        wall_index[wall.id] = wall

    for idx, wall in enumerate(layout.perimeter_walls, start=1):
        wall_id = str(wall.get("id", f"perimeter_{idx}"))
        thickness_mm = _as_float(wall.get("thickness_mm", 100.0), default=100.0)

        # Perimeter wall metadata can be sparse or malformed in model output.
        # Keep validation robust by coercing to a minimal positive thickness.
        if thickness_mm <= 0:
            thickness_mm = 1.0

        wall_index[wall_id] = InteriorWall(
            id=wall_id,
            x1=_as_float(wall.get("x1", 0.0), default=0.0),
            y1=_as_float(wall.get("y1", 0.0), default=0.0),
            x2=_as_float(wall.get("x2", 0.0), default=0.0),
            y2=_as_float(wall.get("y2", 0.0), default=0.0),
            thickness_mm=thickness_mm,
            material=str(wall.get("material", "drywall")),
        )

    return wall_index


def _perimeter_bbox_area_mm2(layout: GeneratedLayout) -> float:
    """Compute perimeter bounding box area in mm^2."""

    coords_x: list[float] = []
    coords_y: list[float] = []
    for wall in layout.perimeter_walls:
        x1 = _as_float(wall.get("x1"), default=float("nan"))
        y1 = _as_float(wall.get("y1"), default=float("nan"))
        x2 = _as_float(wall.get("x2"), default=float("nan"))
        y2 = _as_float(wall.get("y2"), default=float("nan"))
        if all(math.isfinite(v) for v in (x1, y1, x2, y2)):
            coords_x.extend([x1, x2])
            coords_y.extend([y1, y2])

    if coords_x and coords_y:
        width = max(coords_x) - min(coords_x)
        height = max(coords_y) - min(coords_y)
        if width > 0 and height > 0:
            return width * height

    return layout.page_dimensions_mm[0] * layout.page_dimensions_mm[1]


def validate_layout(layout: GeneratedLayout) -> ConstraintResult:
    """Validate a GeneratedLayout against spatial constraints."""

    violations: list[ConstraintViolation] = []

    if not layout.rooms:
        violations.append(
            ConstraintViolation(
                type=ConstraintViolationType.ROOM_NOT_ENCLOSED,
                description="Layout contains no generated rooms.",
                severity="error",
                affected_elements=[],
            )
        )

    room_polygons: dict[str, Polygon] = {}
    for room in layout.rooms:
        polygon = _room_polygon(room.boundary)
        room_polygons[room.name] = polygon

        if (not polygon.is_valid) or polygon.is_empty or polygon.area <= 0:
            violations.append(
                ConstraintViolation(
                    type=ConstraintViolationType.ROOM_NOT_ENCLOSED,
                    description=f"Room '{room.name}' boundary is not a valid enclosed polygon.",
                    severity="error",
                    affected_elements=[room.name],
                )
            )

    room_overlap_tolerance_mm2 = 10_000.0  # 0.01 sqm
    rooms = layout.rooms
    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            room_a = rooms[i]
            room_b = rooms[j]
            poly_a = room_polygons.get(room_a.name)
            poly_b = room_polygons.get(room_b.name)
            if (
                not poly_a
                or not poly_b
                or (not poly_a.is_valid)
                or (not poly_b.is_valid)
            ):
                continue

            overlap_area_mm2 = poly_a.intersection(poly_b).area
            if overlap_area_mm2 > room_overlap_tolerance_mm2:
                overlap_sqm = overlap_area_mm2 / 1_000_000.0
                violations.append(
                    ConstraintViolation(
                        type=ConstraintViolationType.ROOM_OVERLAP,
                        description=(
                            f"{room_a.name} and {room_b.name} overlap by {overlap_sqm:.2f} sqm."
                        ),
                        severity="error",
                        affected_elements=[room_a.name, room_b.name],
                    )
                )

    for room in layout.rooms:
        if room.room_type.lower() not in {"corridor", "hallway", "passage"}:
            continue

        corridor_poly = room_polygons.get(room.name)
        if not corridor_poly or not corridor_poly.is_valid:
            continue

        narrowed = corridor_poly.buffer(-450.0)
        if narrowed.is_empty:
            violations.append(
                ConstraintViolation(
                    type=ConstraintViolationType.CORRIDOR_TOO_NARROW,
                    description=f"{room.name} is narrower than 900mm at one or more points.",
                    severity="error",
                    affected_elements=[room.name],
                )
            )

    wall_index = _build_wall_index(layout)
    wall_geometries: dict[str, Polygon] = {}
    for wall_id, wall in wall_index.items():
        wall_geometries[wall_id] = _wall_polygon(
            wall.x1,
            wall.y1,
            wall.x2,
            wall.y2,
            wall.thickness_mm,
        )

    fixture_geometries = {
        fixture.id: _fixture_polygon(fixture) for fixture in layout.fixtures
    }

    for door in layout.doors:
        if door.door_type == "sliding" or door.swing_direction == "sliding":
            continue

        host_wall = wall_index.get(door.wall_id)
        if host_wall is None:
            violations.append(
                ConstraintViolation(
                    type=ConstraintViolationType.DOOR_SWING_BLOCKED,
                    description=f"Door '{door.id}' references unknown wall '{door.wall_id}'.",
                    severity="error",
                    affected_elements=[door.id, door.wall_id],
                )
            )
            continue

        swing_arc = get_door_swing_arc(host_wall, door)
        if swing_arc.is_empty:
            continue

        blocked = False
        for wall_id, wall_poly in wall_geometries.items():
            if wall_id == door.wall_id:
                continue
            if swing_arc.intersection(wall_poly).area > 0:
                violations.append(
                    ConstraintViolation(
                        type=ConstraintViolationType.DOOR_SWING_BLOCKED,
                        description=f"Door '{door.id}' swing intersects wall '{wall_id}'.",
                        severity="error",
                        affected_elements=[door.id, wall_id],
                    )
                )
                blocked = True
                break

        if blocked:
            continue

        for fixture_id, fixture_poly in fixture_geometries.items():
            if swing_arc.intersection(fixture_poly).area > 0:
                violations.append(
                    ConstraintViolation(
                        type=ConstraintViolationType.DOOR_SWING_BLOCKED,
                        description=f"Door '{door.id}' swing intersects fixture '{fixture_id}'.",
                        severity="error",
                        affected_elements=[door.id, fixture_id],
                    )
                )
                break

    total_room_area_mm2 = 0.0
    for room in layout.rooms:
        poly = room_polygons.get(room.name)
        if poly and poly.is_valid:
            total_room_area_mm2 += poly.area

    perimeter_area_mm2 = _perimeter_bbox_area_mm2(layout)
    if perimeter_area_mm2 > 0 and total_room_area_mm2 > (perimeter_area_mm2 * 1.05):
        violations.append(
            ConstraintViolation(
                type=ConstraintViolationType.AREA_EXCEEDS_PERIMETER,
                description=(
                    f"Total room area {(total_room_area_mm2 / 1_000_000.0):.2f} sqm exceeds "
                    f"perimeter budget {(perimeter_area_mm2 / 1_000_000.0):.2f} sqm."
                ),
                severity="error",
                affected_elements=[room.name for room in layout.rooms],
            )
        )

    room_by_name = {room.name: room_polygons.get(room.name) for room in layout.rooms}
    for fixture in layout.fixtures:
        room_poly = room_by_name.get(fixture.room_name)
        fixture_center = Point(fixture.center_x, fixture.center_y)
        if (
            room_poly is None
            or (not room_poly.is_valid)
            or (not room_poly.covers(fixture_center))
        ):
            violations.append(
                ConstraintViolation(
                    type=ConstraintViolationType.FIXTURE_OUTSIDE_ROOM,
                    description=(
                        f"Fixture '{fixture.id}' center lies outside assigned room '{fixture.room_name}'."
                    ),
                    severity="warning",
                    affected_elements=[fixture.id, fixture.room_name],
                )
            )

    fixtures_by_room: dict[str, list] = defaultdict(list)
    for fixture in layout.fixtures:
        fixtures_by_room[fixture.room_name].append(fixture)

    for room_name, fixtures in fixtures_by_room.items():
        for i in range(len(fixtures)):
            for j in range(i + 1, len(fixtures)):
                fixture_a = fixtures[i]
                fixture_b = fixtures[j]
                poly_a = fixture_geometries[fixture_a.id]
                poly_b = fixture_geometries[fixture_b.id]
                if poly_a.intersection(poly_b).area > 0:
                    violations.append(
                        ConstraintViolation(
                            type=ConstraintViolationType.FIXTURE_OVERLAP,
                            description=(
                                f"Fixtures '{fixture_a.id}' and '{fixture_b.id}' overlap in room '{room_name}'."
                            ),
                            severity="warning",
                            affected_elements=[fixture_a.id, fixture_b.id, room_name],
                        )
                    )

    error_count = sum(1 for violation in violations if violation.severity == "error")
    warning_count = len(violations) - error_count

    return ConstraintResult(
        passed=error_count == 0,
        violations=violations,
        summary=f"{error_count} errors, {warning_count} warnings",
    )
