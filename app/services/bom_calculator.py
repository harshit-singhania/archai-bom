"""Deterministic BOM calculator from layout geometry and material rates."""

import math

from app.models.bom import (
    BASE_ROOM_CATEGORIES,
    BOMLineItem,
    BOMResult,
    DEFAULT_CEILING_HEIGHT_MM,
    M_TO_FT,
    MM_TO_M,
    ROOM_TYPE_MATERIALS,
    SQM_TO_SQFT,
    MaterialInfo,
)
from app.models.layout import Door, GeneratedLayout, GeneratedRoom, InteriorWall


def calculate_bom(
    layout: GeneratedLayout,
    materials: list[MaterialInfo],
    ceiling_height_mm: float = DEFAULT_CEILING_HEIGHT_MM,
) -> BOMResult:
    """Calculate a priced bill of materials from a generated layout."""
    if not layout.rooms and not layout.interior_walls and not layout.doors:
        return BOMResult(
            line_items=[],
            grand_total_inr=0.0,
            room_count=0,
            total_area_sqm=0.0,
        )

    line_items: list[BOMLineItem] = []

    for room in layout.rooms:
        line_items.extend(_calculate_room_bom(room, materials, ceiling_height_mm))

    for wall in layout.interior_walls:
        line_items.extend(_calculate_wall_bom(wall, materials, ceiling_height_mm))

    for door in layout.doors:
        line_items.extend(_calculate_door_bom(door, materials))

    grand_total = round(sum(item.amount_inr for item in line_items), 2)
    total_area_sqm = round(sum(room.area_sqm for room in layout.rooms), 2)
    return BOMResult(
        line_items=line_items,
        grand_total_inr=grand_total,
        room_count=len(layout.rooms),
        total_area_sqm=total_area_sqm,
    )


def _wall_length_mm(wall: InteriorWall) -> float:
    """Return Euclidean wall length in millimeters."""
    return math.hypot(wall.x2 - wall.x1, wall.y2 - wall.y1)


def _room_perimeter_mm(boundary: list[tuple[float, float]]) -> float:
    """Calculate room boundary perimeter in millimeters."""
    if len(boundary) < 2:
        return 0.0

    perimeter_mm = 0.0
    for idx in range(len(boundary) - 1):
        x1, y1 = boundary[idx]
        x2, y2 = boundary[idx + 1]
        perimeter_mm += math.hypot(x2 - x1, y2 - y1)

    if boundary[0] != boundary[-1]:
        x1, y1 = boundary[-1]
        x2, y2 = boundary[0]
        perimeter_mm += math.hypot(x2 - x1, y2 - y1)

    return perimeter_mm


def _find_material(
    materials: list[MaterialInfo],
    category: str,
    preference: str = "",
) -> MaterialInfo | None:
    """Find a material by category, optionally preferring a name substring."""
    category_materials = [m for m in materials if m.category == category]
    if not category_materials:
        return None

    if preference:
        preference_lower = preference.lower()
        for material in category_materials:
            if preference_lower in material.material_name.lower():
                return material

    return category_materials[0]


def _sqm_to_sqft(sqm: float) -> float:
    """Convert square meters to square feet."""
    return sqm * SQM_TO_SQFT


def _mm_to_running_foot(mm: float) -> float:
    """Convert millimeters to running feet."""
    return mm * MM_TO_M * M_TO_FT


def _calculate_room_bom(
    room: GeneratedRoom,
    materials: list[MaterialInfo],
    ceiling_height_mm: float,
) -> list[BOMLineItem]:
    """Calculate room-level BOM categories (flooring, ceiling, paint, etc.)."""
    room_items: list[BOMLineItem] = []
    area_sqft = _sqm_to_sqft(room.area_sqm)
    perimeter_mm = _room_perimeter_mm(room.boundary)
    perimeter_ft = _mm_to_running_foot(perimeter_mm)
    perimeter_m = perimeter_mm * MM_TO_M
    wall_surface_sqft = _sqm_to_sqft(perimeter_m * (ceiling_height_mm * MM_TO_M))
    room_type = room.room_type.lower().strip()

    skip_flooring = room_type in {"server_room", "server"}

    for category in BASE_ROOM_CATEGORIES:
        if skip_flooring and category == "flooring":
            continue

        material = _find_material(materials, category)
        if material is None:
            continue

        if category == "flooring":
            room_items.append(
                _build_line_item(
                    material=material,
                    quantity=area_sqft,
                    room_name=room.name,
                )
            )
        elif category == "ceiling":
            room_items.append(
                _build_line_item(
                    material=material,
                    quantity=area_sqft,
                    room_name=room.name,
                )
            )
        elif category == "baseboard":
            room_items.append(
                _build_line_item(
                    material=material,
                    quantity=perimeter_ft,
                    room_name=room.name,
                )
            )
        elif category == "paint":
            paint_material = _find_material(materials, "paint", preference="emulsion")
            if paint_material is None:
                paint_material = material
            primer_material = _find_material(materials, "paint", preference="primer")

            room_items.append(
                _build_line_item(
                    material=paint_material,
                    quantity=wall_surface_sqft * 2.0,
                    room_name=room.name,
                    notes="Two coats",
                )
            )
            if primer_material is not None:
                room_items.append(
                    _build_line_item(
                        material=primer_material,
                        quantity=wall_surface_sqft,
                        room_name=room.name,
                        notes="One coat primer",
                    )
                )
        elif category == "electrical":
            room_items.extend(_calculate_electrical(room, materials))

    room_items.extend(_calculate_specialty(room, materials, ceiling_height_mm))
    return room_items


def _calculate_wall_bom(
    wall: InteriorWall,
    materials: list[MaterialInfo],
    ceiling_height_mm: float,
) -> list[BOMLineItem]:
    """Calculate BOM for each interior wall using wall area."""
    wall_length_mm = _wall_length_mm(wall)
    wall_area_sqm = (wall_length_mm * ceiling_height_mm) / 1_000_000
    wall_area_sqft = _sqm_to_sqft(wall_area_sqm)

    preferred_material = _find_material(materials, "wall", preference=wall.material)
    if preferred_material is None:
        preferred_material = _find_material(materials, "wall")
    if preferred_material is None:
        return []

    return [
        _build_line_item(
            material=preferred_material,
            quantity=wall_area_sqft,
            notes=f"Interior wall {wall.id}",
        )
    ]


def _calculate_door_bom(door: Door, materials: list[MaterialInfo]) -> list[BOMLineItem]:
    """Create door panel plus hardware line items for each door."""
    items: list[BOMLineItem] = []

    door_preference = {
        "single": "flush",
        "double": "fire",
        "sliding": "sliding",
    }.get(door.door_type, "")
    door_material = _find_material(materials, "door", preference=door_preference)
    if door_material is None:
        door_material = _find_material(materials, "door")

    if door_material is not None:
        items.append(
            _build_line_item(
                material=door_material,
                quantity=1.0,
                notes=f"Door panel for {door.id}",
            )
        )

    frame_material = _find_material(materials, "door_hardware", preference="frame")
    if frame_material is not None:
        frame_running_foot = _mm_to_running_foot(door.width_mm + (2100.0 * 2))
        items.append(
            _build_line_item(
                material=frame_material,
                quantity=frame_running_foot,
                notes=f"Door frame for {door.id}",
            )
        )

    handle_material = _find_material(materials, "door_hardware", preference="handle")
    if handle_material is not None:
        items.append(
            _build_line_item(
                material=handle_material,
                quantity=1.0,
                notes=f"Handle set for {door.id}",
            )
        )

    closer_material = _find_material(materials, "door_hardware", preference="closer")
    if closer_material is not None:
        items.append(
            _build_line_item(
                material=closer_material,
                quantity=1.0,
                notes=f"Closer for {door.id}",
            )
        )

    return items


def _calculate_electrical(
    room: GeneratedRoom, materials: list[MaterialInfo]
) -> list[BOMLineItem]:
    """Estimate electrical points by room area."""
    items: list[BOMLineItem] = []
    lights_count = float(math.ceil(room.area_sqm / 4.0))
    sockets_count = float(max(2, math.ceil(room.area_sqm / 3.0)))

    light_material = _find_material(materials, "electrical", preference="light")
    socket_material = _find_material(materials, "electrical", preference="socket")
    switch_material = _find_material(materials, "electrical", preference="switch")

    if light_material is not None:
        items.append(
            _build_line_item(
                material=light_material,
                quantity=lights_count,
                room_name=room.name,
            )
        )
    if socket_material is not None:
        items.append(
            _build_line_item(
                material=socket_material,
                quantity=sockets_count,
                room_name=room.name,
            )
        )
    if switch_material is not None:
        items.append(
            _build_line_item(
                material=switch_material,
                quantity=1.0,
                room_name=room.name,
            )
        )

    return items


def _calculate_specialty(
    room: GeneratedRoom,
    materials: list[MaterialInfo],
    ceiling_height_mm: float,
) -> list[BOMLineItem]:
    """Apply room-type-specific BOM categories."""
    room_type = room.room_type.lower().strip()
    extra_categories = ROOM_TYPE_MATERIALS.get(room_type, [])
    if not extra_categories:
        return []

    items: list[BOMLineItem] = []
    area_sqft = _sqm_to_sqft(room.area_sqm)
    perimeter_mm = _room_perimeter_mm(room.boundary)
    perimeter_m = perimeter_mm * MM_TO_M

    for category in extra_categories:
        if category == "waterproofing":
            material = _find_material(materials, "waterproofing")
            if material is None:
                continue

            waterproof_wall_sqm = perimeter_m * 1.5
            total_waterproof_sqft = area_sqft + _sqm_to_sqft(waterproof_wall_sqm)
            items.append(
                _build_line_item(
                    material=material,
                    quantity=total_waterproof_sqft,
                    room_name=room.name,
                    notes="Floor + walls up to 1.5m",
                )
            )

        if category == "specialty":
            if room_type in {"kitchen", "pantry"}:
                material = _find_material(
                    materials, "specialty", preference="backsplash"
                )
                if material is None:
                    material = _find_material(materials, "specialty")
                if material is None:
                    continue

                backsplash_sqm = perimeter_m * 0.6
                items.append(
                    _build_line_item(
                        material=material,
                        quantity=_sqm_to_sqft(backsplash_sqm),
                        room_name=room.name,
                        notes="Backsplash up to 600mm",
                    )
                )
            elif room_type in {"server_room", "server"}:
                material = _find_material(materials, "specialty", preference="raised")
                if material is None:
                    material = _find_material(materials, "specialty")
                if material is None:
                    continue

                items.append(
                    _build_line_item(
                        material=material,
                        quantity=area_sqft,
                        room_name=room.name,
                        notes="Raised flooring replacing standard flooring",
                    )
                )
            elif room_type == "lab":
                material = _find_material(
                    materials, "specialty", preference="anti-static"
                )
                if material is None:
                    material = _find_material(materials, "specialty")
                if material is None:
                    continue

                items.append(
                    _build_line_item(
                        material=material,
                        quantity=area_sqft,
                        room_name=room.name,
                        notes="Specialty finish for lab",
                    )
                )

    return items


def _build_line_item(
    material: MaterialInfo,
    quantity: float,
    room_name: str | None = None,
    notes: str | None = None,
) -> BOMLineItem:
    """Build a rounded BOM line item from material and quantity."""
    rounded_quantity = round(quantity, 2)
    amount_inr = round(rounded_quantity * material.cost_inr, 2)
    return BOMLineItem(
        material_name=material.material_name,
        category=material.category,
        quantity=rounded_quantity,
        unit=material.unit_of_measurement,
        rate_inr=material.cost_inr,
        amount_inr=amount_inr,
        room_name=room_name,
        notes=notes,
    )
