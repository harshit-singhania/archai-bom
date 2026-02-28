"""Integration-style tests for layout-to-BOM deterministic calculation."""

import pytest

from app.models.bom import MaterialInfo
from app.models.layout import GeneratedLayout
from app.services.bom_calculator import calculate_bom


@pytest.fixture
def sample_materials() -> list[MaterialInfo]:
    """Fixture materials representing one choice per major category."""
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
            material_name="Sliding Glass Door Panel",
            category="door",
            unit_of_measurement="piece",
            cost_inr=16000.0,
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
    """Office layout with two rooms, two walls, and two doors."""
    return GeneratedLayout(
        rooms=[
            {
                "name": "Reception",
                "room_type": "office",
                "boundary": [
                    (0.0, 0.0),
                    (4000.0, 0.0),
                    (4000.0, 5000.0),
                    (0.0, 5000.0),
                    (0.0, 0.0),
                ],
                "area_sqm": 20.0,
            },
            {
                "name": "Meeting Room",
                "room_type": "meeting_room",
                "boundary": [
                    (4500.0, 0.0),
                    (7500.0, 0.0),
                    (7500.0, 4000.0),
                    (4500.0, 4000.0),
                    (4500.0, 0.0),
                ],
                "area_sqm": 12.0,
            },
        ],
        interior_walls=[
            {
                "id": "iw_1",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 5000.0,
                "y2": 0.0,
                "thickness_mm": 100.0,
                "material": "drywall",
            },
            {
                "id": "iw_2",
                "x1": 0.0,
                "y1": 2000.0,
                "x2": 4000.0,
                "y2": 2000.0,
                "thickness_mm": 100.0,
                "material": "drywall",
            },
        ],
        doors=[
            {
                "id": "d_1",
                "wall_id": "iw_1",
                "position_along_wall": 0.4,
                "width_mm": 900.0,
                "swing_direction": "left",
                "door_type": "single",
            },
            {
                "id": "d_2",
                "wall_id": "iw_2",
                "position_along_wall": 0.6,
                "width_mm": 1200.0,
                "swing_direction": "sliding",
                "door_type": "sliding",
            },
        ],
        fixtures=[],
        grid_size_mm=50,
        prompt="office layout",
        perimeter_walls=[],
        page_dimensions_mm=(10000.0, 8000.0),
    )


@pytest.fixture
def bathroom_layout() -> GeneratedLayout:
    """Bathroom layout with one room, one wall, and one door."""
    return GeneratedLayout(
        rooms=[
            {
                "name": "Bathroom 1",
                "room_type": "bathroom",
                "boundary": [
                    (0.0, 0.0),
                    (2000.0, 0.0),
                    (2000.0, 3000.0),
                    (0.0, 3000.0),
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
        prompt="bathroom layout",
        perimeter_walls=[],
        page_dimensions_mm=(6000.0, 5000.0),
    )


def test_office_bom_has_all_base_categories(sample_materials, office_layout):
    """Office rooms produce expected base categories without waterproofing."""
    result = calculate_bom(office_layout, sample_materials)
    categories = {item.category for item in result.line_items}

    assert "flooring" in categories
    assert "ceiling" in categories
    assert "paint" in categories
    assert "electrical" in categories
    assert "baseboard" in categories
    assert "wall" in categories
    assert "waterproofing" not in categories


def test_bathroom_includes_waterproofing(sample_materials, bathroom_layout):
    """Bathroom rooms produce waterproofing items."""
    result = calculate_bom(bathroom_layout, sample_materials)
    categories = {item.category for item in result.line_items}

    assert "waterproofing" in categories


def test_different_room_types_produce_different_materials(
    sample_materials,
    office_layout,
    bathroom_layout,
):
    """Office and bathroom category sets should differ."""
    office_result = calculate_bom(office_layout, sample_materials)
    bathroom_result = calculate_bom(bathroom_layout, sample_materials)

    office_categories = {item.category for item in office_result.line_items}
    bathroom_categories = {item.category for item in bathroom_result.line_items}
    assert bathroom_categories - office_categories


def test_grand_total_equals_sum_of_amounts(sample_materials, office_layout):
    """Grand total must equal sum of all line-item amounts."""
    result = calculate_bom(office_layout, sample_materials)
    expected_total = sum(item.amount_inr for item in result.line_items)
    assert abs(result.grand_total_inr - expected_total) < 0.01


def test_wall_quantity_is_geometrically_correct(sample_materials, office_layout):
    """Wall quantity reflects wall area = length x height."""
    result = calculate_bom(office_layout, sample_materials)
    wall_items = [item for item in result.line_items if item.category == "wall"]

    assert len(wall_items) > 0
    total_wall_sqft = sum(item.quantity for item in wall_items)
    assert total_wall_sqft > 200
    assert total_wall_sqft < 350


def test_flooring_quantity_matches_room_area(sample_materials, office_layout):
    """Flooring quantity should match room area in sqft."""
    result = calculate_bom(office_layout, sample_materials)
    flooring_items = [item for item in result.line_items if item.category == "flooring"]
    total_flooring_sqft = sum(item.quantity for item in flooring_items)

    assert total_flooring_sqft > 300
    assert total_flooring_sqft < 400


def test_empty_layout_produces_empty_bom(sample_materials):
    """No rooms should produce empty BOM with zero totals."""
    empty = GeneratedLayout(
        rooms=[],
        interior_walls=[],
        doors=[],
        fixtures=[],
        grid_size_mm=50,
        prompt="empty",
        perimeter_walls=[],
        page_dimensions_mm=(10000, 8000),
    )

    result = calculate_bom(empty, sample_materials)
    assert result.grand_total_inr == 0.0
    assert len(result.line_items) == 0


def test_each_door_generates_multiple_items(sample_materials, office_layout):
    """Each door should generate panel and hardware items."""
    result = calculate_bom(office_layout, sample_materials)
    door_items = [
        item for item in result.line_items if item.category in ("door", "door_hardware")
    ]

    assert len(door_items) >= 8


def test_bom_result_has_correct_room_count(sample_materials, office_layout):
    """room_count should equal number of rooms in the layout."""
    result = calculate_bom(office_layout, sample_materials)
    assert result.room_count == 2


def test_amount_equals_quantity_times_rate(sample_materials, office_layout):
    """Every amount must be quantity x rate."""
    result = calculate_bom(office_layout, sample_materials)

    for item in result.line_items:
        expected = round(item.quantity * item.rate_inr, 2)
        assert abs(item.amount_inr - expected) < 0.01
