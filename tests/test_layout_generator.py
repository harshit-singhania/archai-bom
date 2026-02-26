"""Tests for Gemini layout generation service."""

from unittest.mock import MagicMock, patch

import pytest

from app.models.geometry import WallSegment
from app.models.layout import GeneratedLayout
from app.models.spatial import Room, SpatialGraph
from app.services.layout_generator import generate_layout


def _simple_spatial_graph() -> SpatialGraph:
    """Create a 10m x 8m rectangular perimeter graph."""

    walls = [
        WallSegment(
            x1=0.0, y1=0.0, x2=10000.0, y2=0.0, length_pts=10000.0, thickness=200.0
        ),
        WallSegment(
            x1=10000.0,
            y1=0.0,
            x2=10000.0,
            y2=8000.0,
            length_pts=8000.0,
            thickness=200.0,
        ),
        WallSegment(
            x1=10000.0,
            y1=8000.0,
            x2=0.0,
            y2=8000.0,
            length_pts=10000.0,
            thickness=200.0,
        ),
        WallSegment(
            x1=0.0, y1=8000.0, x2=0.0, y2=0.0, length_pts=8000.0, thickness=200.0
        ),
    ]
    rooms = [
        Room(name="Existing Shell", boundary_walls=[0, 1, 2, 3], area_sq_pts=80000000.0)
    ]
    return SpatialGraph(
        walls=walls, rooms=rooms, scale_factor=None, page_dimensions=(10000.0, 8000.0)
    )


def _simple_spatial_graph_with_unscaled_factor() -> SpatialGraph:
    walls = [
        WallSegment(
            x1=0.0, y1=0.0, x2=10000.0, y2=0.0, length_pts=10000.0, thickness=200.0
        )
    ]
    return SpatialGraph(
        walls=walls,
        rooms=[],
        scale_factor=1.0,
        page_dimensions=(10000.0, 8000.0),
    )


def _generated_layout_payload() -> dict:
    return {
        "rooms": [
            {
                "name": "Reception",
                "room_type": "reception",
                "boundary": [
                    [0.0, 0.0],
                    [3500.0, 0.0],
                    [3500.0, 2500.0],
                    [0.0, 2500.0],
                    [0.0, 0.0],
                ],
                "area_sqm": 8.75,
            }
        ],
        "interior_walls": [
            {
                "id": "iw_1",
                "x1": 3500.0,
                "y1": 0.0,
                "x2": 3500.0,
                "y2": 8000.0,
                "thickness_mm": 100.0,
                "material": "drywall",
            }
        ],
        "doors": [
            {
                "id": "d_1",
                "wall_id": "iw_1",
                "position_along_wall": 0.4,
                "width_mm": 900.0,
                "swing_direction": "left",
                "door_type": "single",
            }
        ],
        "fixtures": [
            {
                "id": "f_1",
                "room_name": "Reception",
                "fixture_type": "reception_counter",
                "center_x": 1700.0,
                "center_y": 1200.0,
                "width_mm": 1800.0,
                "depth_mm": 700.0,
                "rotation_deg": 0.0,
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
        "page_dimensions_mm": [10000.0, 8000.0],
    }


@patch("app.services.layout_generator.genai.Client")
def test_generate_layout_success(mock_genai_client, monkeypatch):
    """generate_layout returns a validated GeneratedLayout from mocked Gemini response."""

    monkeypatch.setattr(
        "app.services.layout_generator.settings.GOOGLE_API_KEY", "test_key"
    )

    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.parsed = _generated_layout_payload()
    mock_client.models.generate_content.return_value = mock_response

    spatial_graph = _simple_spatial_graph()
    user_prompt = "6 operatory dental clinic with reception"
    result = generate_layout(spatial_graph=spatial_graph, prompt=user_prompt)

    assert isinstance(result, GeneratedLayout)
    assert result.rooms[0].name == "Reception"
    assert result.page_dimensions_mm == (10000.0, 8000.0)

    call = mock_client.models.generate_content.call_args
    prompt_text = call.kwargs["contents"][0]
    config = call.kwargs["config"]
    assert "Perimeter walls in millimeters" in prompt_text
    assert "10000.0" in prompt_text
    assert user_prompt in prompt_text
    assert config.response_json_schema is not None
    assert config.response_schema is None


@patch("app.services.layout_generator.genai.Client")
def test_generate_layout_malformed_response_raises_value_error(
    mock_genai_client, monkeypatch
):
    """Malformed Gemini response should raise ValueError."""

    monkeypatch.setattr(
        "app.services.layout_generator.settings.GOOGLE_API_KEY", "test_key"
    )

    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = "{not valid json"
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="non-JSON response"):
        generate_layout(spatial_graph=_simple_spatial_graph(), prompt="simple clinic")


@patch("app.services.layout_generator.genai.Client")
def test_generate_layout_scale_factor_one_uses_mm_fallback(
    mock_genai_client, monkeypatch
):
    """scale_factor=1.0 should use 1pt=1mm fallback, not feet conversion."""

    monkeypatch.setattr(
        "app.services.layout_generator.settings.GOOGLE_API_KEY", "test_key"
    )

    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.parsed = _generated_layout_payload()
    mock_client.models.generate_content.return_value = mock_response

    generate_layout(
        spatial_graph=_simple_spatial_graph_with_unscaled_factor(),
        prompt="office",
    )

    prompt_text = mock_client.models.generate_content.call_args.kwargs["contents"][0]
    assert "6096000" not in prompt_text
    assert '"width_mm": 10000.0' in prompt_text
