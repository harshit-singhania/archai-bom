"""Tests for Gemini layout generation service."""

from unittest.mock import MagicMock, call, patch

import pytest

from app.models.geometry import WallSegment
from app.models.layout import GeneratedLayout
from app.models.spatial import Room, SpatialGraph
from app.integrations.layout_generator import (
    _call_gemini_with_retry,
    _call_gemini_with_timeout,
    generate_layout,
)


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


@patch("app.integrations.layout_generator.genai.Client")
def test_generate_layout_success(mock_genai_client, monkeypatch):
    """generate_layout returns a validated GeneratedLayout from mocked Gemini response."""

    monkeypatch.setattr(
        "app.integrations.layout_generator.settings.GOOGLE_API_KEY", "test_key"
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


@patch("app.integrations.layout_generator.genai.Client")
def test_generate_layout_malformed_response_raises_value_error(
    mock_genai_client, monkeypatch
):
    """Malformed Gemini response should raise ValueError."""

    monkeypatch.setattr(
        "app.integrations.layout_generator.settings.GOOGLE_API_KEY", "test_key"
    )

    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = "{not valid json"
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="non-JSON response"):
        generate_layout(spatial_graph=_simple_spatial_graph(), prompt="simple clinic")


@patch("app.integrations.layout_generator.genai.Client")
def test_generate_layout_scale_factor_one_uses_mm_fallback(
    mock_genai_client, monkeypatch
):
    """scale_factor=1.0 should use 1pt=1mm fallback, not feet conversion."""

    monkeypatch.setattr(
        "app.integrations.layout_generator.settings.GOOGLE_API_KEY", "test_key"
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


# --- Timeout / Retry / Backoff tests ---


@patch("app.integrations.layout_generator._call_gemini_with_timeout")
@patch("app.integrations.layout_generator.time.sleep")
def test_retry_succeeds_after_transient_failure(mock_sleep, mock_timeout_call):
    """Transient RuntimeError on first attempt should retry and succeed."""

    mock_client = MagicMock()
    good_response = MagicMock()
    mock_timeout_call.side_effect = [RuntimeError("connection reset"), good_response]

    result = _call_gemini_with_retry(
        client=mock_client,
        generation_prompt="test prompt",
        max_retries=2,
        timeout_seconds=10.0,
        base_delay=0.1,
        max_delay=5.0,
    )

    assert result is good_response
    assert mock_timeout_call.call_count == 2
    # One sleep between attempt 1 and attempt 2
    mock_sleep.assert_called_once()


@patch("app.integrations.layout_generator._call_gemini_with_timeout")
@patch("app.integrations.layout_generator.time.sleep")
def test_retry_exhaustion_raises_runtime_error(mock_sleep, mock_timeout_call):
    """After all retries exhausted, RuntimeError should propagate."""

    mock_client = MagicMock()
    mock_timeout_call.side_effect = RuntimeError("timeout or transient failure")

    with pytest.raises(RuntimeError, match="failed after"):
        _call_gemini_with_retry(
            client=mock_client,
            generation_prompt="test prompt",
            max_retries=2,
            timeout_seconds=10.0,
            base_delay=0.1,
            max_delay=5.0,
        )

    # 1 initial + 2 retries = 3 total attempts
    assert mock_timeout_call.call_count == 3
    # Sleep between attempts 1->2 and 2->3
    assert mock_sleep.call_count == 2


@patch("app.integrations.layout_generator._call_gemini_with_timeout")
@patch("app.integrations.layout_generator.time.sleep")
def test_non_transient_exception_not_retried(mock_sleep, mock_timeout_call):
    """Non-RuntimeError SDK exceptions should not be retried."""

    mock_client = MagicMock()
    mock_timeout_call.side_effect = ValueError("bad model name")

    with pytest.raises(RuntimeError, match="Gemini layout generation failed"):
        _call_gemini_with_retry(
            client=mock_client,
            generation_prompt="test prompt",
            max_retries=3,
            timeout_seconds=10.0,
            base_delay=0.1,
            max_delay=5.0,
        )

    # Only one attempt — no retries for non-transient
    assert mock_timeout_call.call_count == 1
    mock_sleep.assert_not_called()


@patch("app.integrations.layout_generator._call_gemini_with_timeout")
@patch("app.integrations.layout_generator.time.sleep")
def test_exponential_backoff_delays_increase(mock_sleep, mock_timeout_call):
    """Backoff delays should double each retry attempt."""

    mock_client = MagicMock()
    mock_timeout_call.side_effect = RuntimeError("transient")

    with pytest.raises(RuntimeError):
        _call_gemini_with_retry(
            client=mock_client,
            generation_prompt="test prompt",
            max_retries=3,
            timeout_seconds=10.0,
            base_delay=1.0,
            max_delay=100.0,
        )

    # Delays: 1.0, 2.0, 4.0 (3 retries, 3 sleeps)
    sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
    assert sleep_calls == [1.0, 2.0, 4.0]


@patch("app.integrations.layout_generator._call_gemini_with_timeout")
@patch("app.integrations.layout_generator.time.sleep")
def test_backoff_delay_capped_at_max(mock_sleep, mock_timeout_call):
    """Backoff delay should not exceed max_delay."""

    mock_client = MagicMock()
    mock_timeout_call.side_effect = RuntimeError("transient")

    with pytest.raises(RuntimeError):
        _call_gemini_with_retry(
            client=mock_client,
            generation_prompt="test prompt",
            max_retries=5,
            timeout_seconds=10.0,
            base_delay=1.0,
            max_delay=3.0,  # caps delay at 3.0
        )

    # Delays should be capped: 1.0, 2.0, 3.0, 3.0, 3.0
    sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
    assert all(d <= 3.0 for d in sleep_calls)
    assert sleep_calls[2] == 3.0


@patch("app.integrations.layout_generator.genai.Client")
def test_generate_layout_uses_config_timeout_retry(mock_genai_client, monkeypatch):
    """generate_layout passes config timeout/retry values to the retry wrapper."""

    monkeypatch.setattr(
        "app.integrations.layout_generator.settings.GOOGLE_API_KEY", "test_key"
    )
    monkeypatch.setattr(
        "app.integrations.layout_generator.settings.GENERATION_TIMEOUT_SECONDS", 45.0
    )
    monkeypatch.setattr(
        "app.integrations.layout_generator.settings.GENERATION_MAX_RETRIES", 1
    )
    monkeypatch.setattr(
        "app.integrations.layout_generator.settings.GENERATION_RETRY_BASE_DELAY", 0.5
    )
    monkeypatch.setattr(
        "app.integrations.layout_generator.settings.GENERATION_RETRY_MAX_DELAY", 10.0
    )

    mock_client = MagicMock()
    mock_genai_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.parsed = _generated_layout_payload()
    mock_client.models.generate_content.return_value = mock_response

    with patch(
        "app.integrations.layout_generator._call_gemini_with_retry",
        wraps=__import__(
            "app.integrations.layout_generator", fromlist=["_call_gemini_with_retry"]
        )._call_gemini_with_retry,
    ) as mock_retry:
        result = generate_layout(
            spatial_graph=_simple_spatial_graph(), prompt="dental clinic"
        )

    assert isinstance(result, GeneratedLayout)
    # Verify the retry function was invoked with config-derived parameters
    mock_retry.assert_called_once()
    call_kwargs = mock_retry.call_args.kwargs
    assert call_kwargs["max_retries"] == 1
    assert call_kwargs["timeout_seconds"] == 45.0
    assert call_kwargs["base_delay"] == 0.5
    assert call_kwargs["max_delay"] == 10.0
