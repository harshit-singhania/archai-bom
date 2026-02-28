"""Unit tests for deterministic BOM calculator geometry rules."""

import pytest

from app.models.bom import MaterialInfo
from app.models.layout import GeneratedLayout
from app.services.bom_calculator import calculate_bom


@pytest.fixture
def sample_materials() -> list[MaterialInfo]:
    """Minimal material catalog spanning all calculator categories."""
    return [
        MaterialInfo(
            material_name="Standard Gypsum Drywall (12mm)",
            category="wall",
            unit_of_measurement="sqft",
            cost_inr=48.0,
        ),
        MaterialInfo(
            material_name="Vitrified Tiles (600x600mm)",
            category="flooring",
            unit_of_measurement="sqft",
            cost_inr=45.0,
        ),
        MaterialInfo(
            material_name="Gypsum False Ceiling (plain)",
            category="ceiling",
            unit_of_measurement="sqft",
            cost_inr=65.0,
        ),
        MaterialInfo(
            material_name="Interior Acrylic Emulsion (per coat)",
            category="paint",
            unit_of_measurement="sqft",
            cost_inr=14.0,
        ),
        MaterialInfo(
            material_name="Wall Primer (1 coat)",
            category="paint",
            unit_of_measurement="sqft",
            cost_inr=8.0,
        ),
        MaterialInfo(
            material_name="LED Panel Light Point (with wiring)",
            category="electrical",
            unit_of_measurement="piece",
            cost_inr=850.0,
        ),
        MaterialInfo(
            material_name="Power Socket (5A modular)",
            category="electrical",
            unit_of_measurement="piece",
            cost_inr=380.0,
        ),
        MaterialInfo(
            material_name="Modular Switch Board (4-module)",
            category="electrical",
            unit_of_measurement="piece",
            cost_inr=480.0,
        ),
        MaterialInfo(
            material_name="PVC Skirting (75mm)",
            category="baseboard",
            unit_of_measurement="running_foot",
            cost_inr=28.0,
        ),
        MaterialInfo(
            material_name="HDF Flush Door (35mm)",
            category="door",
            unit_of_measurement="piece",
            cost_inr=4800.0,
        ),
        MaterialInfo(
            material_name="Aluminum Door Frame",
            category="door_hardware",
            unit_of_measurement="running_foot",
            cost_inr=195.0,
        ),
        MaterialInfo(
            material_name="Stainless Steel Handle Set",
            category="door_hardware",
            unit_of_measurement="piece",
            cost_inr=650.0,
        ),
        MaterialInfo(
            material_name="Hydraulic Door Closer",
            category="door_hardware",
            unit_of_measurement="piece",
            cost_inr=1200.0,
        ),
        MaterialInfo(
            material_name="Cementitious Waterproofing (2-coat)",
            category="waterproofing",
            unit_of_measurement="sqft",
            cost_inr=38.0,
        ),
        MaterialInfo(
            material_name="Kitchen Backsplash Tiles (ceramic)",
            category="specialty",
            unit_of_measurement="sqft",
            cost_inr=78.0,
        ),
        MaterialInfo(
            material_name="Raised Access Flooring (steel pedestal)",
            category="specialty",
            unit_of_measurement="sqft",
            cost_inr=235.0,
        ),
    ]


@pytest.fixture
def office_layout() -> GeneratedLayout:
    """Single office room (3m x 4m), one wall, one single door."""
    return GeneratedLayout(
        rooms=[
            {
                "name": "Office 1",
                "room_type": "office",
                "boundary": [
                    (0.0, 0.0),
                    (3000.0, 0.0),
                    (3000.0, 4000.0),
                    (0.0, 4000.0),
                    (0.0, 0.0),
                ],
                "area_sqm": 12.0,
            }
        ],
        interior_walls=[
            {
                "id": "iw_1",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 3000.0,
                "y2": 0.0,
                "thickness_mm": 100.0,
                "material": "drywall",
            }
        ],
        doors=[
            {
                "id": "d_1",
                "wall_id": "iw_1",
                "position_along_wall": 0.5,
                "width_mm": 900.0,
                "swing_direction": "left",
                "door_type": "single",
            }
        ],
        fixtures=[],
        grid_size_mm=50,
        prompt="single office",
        perimeter_walls=[],
        page_dimensions_mm=(10000.0, 8000.0),
    )


@pytest.fixture
def bathroom_layout() -> GeneratedLayout:
    """Bathroom room (3m x 2m), one wall, one single door."""
    return GeneratedLayout(
        rooms=[
            {
                "name": "Bathroom 1",
                "room_type": "bathroom",
                "boundary": [
                    (0.0, 0.0),
                    (3000.0, 0.0),
                    (3000.0, 2000.0),
                    (0.0, 2000.0),
                    (0.0, 0.0),
                ],
                "area_sqm": 6.0,
            }
        ],
        interior_walls=[
            {
                "id": "iw_b1",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 3000.0,
                "y2": 0.0,
                "thickness_mm": 100.0,
                "material": "drywall",
            }
        ],
        doors=[
            {
                "id": "d_b1",
                "wall_id": "iw_b1",
                "position_along_wall": 0.4,
                "width_mm": 900.0,
                "swing_direction": "left",
                "door_type": "single",
            }
        ],
        fixtures=[],
        grid_size_mm=50,
        prompt="single bathroom",
        perimeter_walls=[],
        page_dimensions_mm=(8000.0, 6000.0),
    )


def test_single_office_geometry_to_quantity(sample_materials, office_layout):
    """Wall area, floor area, perimeter, door count, and electrical are derived from geometry."""
    result = calculate_bom(office_layout, sample_materials)

    flooring_items = [item for item in result.line_items if item.category == "flooring"]
    ceiling_items = [item for item in result.line_items if item.category == "ceiling"]
    baseboard_items = [
        item for item in result.line_items if item.category == "baseboard"
    ]
    wall_items = [item for item in result.line_items if item.category == "wall"]
    light_items = [
        item
        for item in result.line_items
        if item.material_name.startswith("LED Panel Light")
    ]
    socket_items = [
        item
        for item in result.line_items
        if item.material_name.startswith("Power Socket")
    ]
    switch_items = [
        item
        for item in result.line_items
        if item.material_name.startswith("Modular Switch")
    ]
    door_related = [
        item for item in result.line_items if item.category in ("door", "door_hardware")
    ]

    assert len(flooring_items) == 1
    assert flooring_items[0].quantity == pytest.approx(129.17, abs=0.2)
    assert len(ceiling_items) == 1
    assert ceiling_items[0].quantity == pytest.approx(129.17, abs=0.2)
    assert len(baseboard_items) == 1
    assert baseboard_items[0].quantity == pytest.approx(45.93, abs=0.2)

    assert len(wall_items) == 1
    assert wall_items[0].quantity == pytest.approx(87.19, abs=0.2)

    assert len(light_items) == 1
    assert light_items[0].quantity == 3.0
    assert len(socket_items) == 1
    assert socket_items[0].quantity == 4.0
    assert len(switch_items) == 1
    assert switch_items[0].quantity == 1.0

    assert len(door_related) >= 4


def test_bathroom_room_type_adds_waterproofing(sample_materials, bathroom_layout):
    """Bathroom rooms include waterproofing quantities in addition to base categories."""
    result = calculate_bom(bathroom_layout, sample_materials)
    waterproof_items = [
        item for item in result.line_items if item.category == "waterproofing"
    ]

    assert len(waterproof_items) == 1
    assert waterproof_items[0].quantity > 200


def test_different_room_types_produce_different_materials(
    sample_materials, office_layout, bathroom_layout
):
    """Office and bathroom should not yield identical category sets."""
    office_result = calculate_bom(office_layout, sample_materials)
    bathroom_result = calculate_bom(bathroom_layout, sample_materials)

    office_categories = {item.category for item in office_result.line_items}
    bathroom_categories = {item.category for item in bathroom_result.line_items}

    assert "waterproofing" not in office_categories
    assert "waterproofing" in bathroom_categories
    assert bathroom_categories - office_categories


def test_empty_layout_returns_zero_bom(sample_materials):
    """No rooms, walls, or doors should produce empty BOM with zero total."""
    empty_layout = GeneratedLayout(
        rooms=[],
        interior_walls=[],
        doors=[],
        fixtures=[],
        grid_size_mm=50,
        prompt="empty",
        perimeter_walls=[],
        page_dimensions_mm=(10000.0, 8000.0),
    )

    result = calculate_bom(empty_layout, sample_materials)

    assert result.line_items == []
    assert result.grand_total_inr == 0.0
    assert result.room_count == 0
    assert result.total_area_sqm == 0.0


def test_grand_total_equals_sum_of_line_item_amounts(sample_materials, office_layout):
    """grand_total_inr must be the sum of all item amounts."""
    result = calculate_bom(office_layout, sample_materials)
    expected_total = round(sum(item.amount_inr for item in result.line_items), 2)

    assert result.grand_total_inr == pytest.approx(expected_total, abs=0.01)


def test_line_item_amount_is_quantity_times_rate(sample_materials, office_layout):
    """Each line item amount should equal quantity multiplied by rate."""
    result = calculate_bom(office_layout, sample_materials)

    for item in result.line_items:
        expected = round(item.quantity * item.rate_inr, 2)
        assert item.amount_inr == pytest.approx(expected, abs=0.01)
