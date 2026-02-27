"""Tests for self-correcting generation pipeline."""

from unittest.mock import patch

import pytest

from app.models.constraints import (
    ConstraintResult,
    ConstraintViolation,
    ConstraintViolationType,
)
from app.models.generation import GenerationResult
from app.models.layout import GeneratedLayout
from app.models.spatial import SpatialGraph
from app.services.generation_pipeline import (
    _compute_adaptive_candidates,
    generate_validated_layout,
)


def _spatial_graph() -> SpatialGraph:
    return SpatialGraph(
        walls=[
            {
                "x1": 0.0,
                "y1": 0.0,
                "x2": 10000.0,
                "y2": 0.0,
                "length_pts": 10000.0,
                "thickness": 2.0,
            }
        ],
        rooms=[],
        scale_factor=None,
        page_dimensions=(10000.0, 8000.0),
    )


def _layout() -> GeneratedLayout:
    return GeneratedLayout(
        rooms=[
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
            }
        ],
        interior_walls=[],
        doors=[],
        fixtures=[],
        grid_size_mm=50,
        prompt="test",
        perimeter_walls=[],
        page_dimensions_mm=(10000.0, 8000.0),
    )


def _constraint_result(passed: bool) -> ConstraintResult:
    if passed:
        return ConstraintResult(
            passed=True, violations=[], summary="0 errors, 0 warnings"
        )

    violation = ConstraintViolation(
        type=ConstraintViolationType.ROOM_OVERLAP,
        description="Room A and Room B overlap by 2.30 sqm.",
        severity="error",
        affected_elements=["Room A", "Room B"],
    )
    return ConstraintResult(
        passed=False, violations=[violation], summary="1 errors, 0 warnings"
    )


def _warning_only_constraint_result() -> ConstraintResult:
    """ConstraintResult with only warnings (no blocking errors), failed=False."""
    warning = ConstraintViolation(
        type=ConstraintViolationType.ROOM_OVERLAP,
        description="Fixture slightly outside room boundary.",
        severity="warning",
        affected_elements=["f_1"],
    )
    return ConstraintResult(
        passed=False, violations=[warning], summary="0 errors, 1 warnings"
    )


@patch("app.services.generation_pipeline.validate_layout")
@patch("app.services.generation_pipeline.snap_layout_to_grid")
@patch("app.services.generation_pipeline.generate_layout")
def test_generate_validated_layout_happy_path(
    mock_generate_layout, mock_snap_layout_to_grid, mock_validate_layout
):
    """Valid first attempt should succeed in one iteration."""

    generated = _layout()
    mock_generate_layout.return_value = generated
    mock_snap_layout_to_grid.return_value = generated
    mock_validate_layout.return_value = _constraint_result(passed=True)

    result = generate_validated_layout(
        spatial_graph=_spatial_graph(), prompt="open-plan office"
    )

    assert isinstance(result, GenerationResult)
    assert result.success is True
    assert result.iterations_used == 1
    assert len(result.constraint_history) == 1
    assert mock_generate_layout.call_count == 1


@patch("app.services.generation_pipeline.validate_layout")
@patch("app.services.generation_pipeline.snap_layout_to_grid")
@patch("app.services.generation_pipeline.generate_layout")
def test_generate_validated_layout_retries_then_succeeds(
    mock_generate_layout, mock_snap_layout_to_grid, mock_validate_layout
):
    """Invalid first attempt should retry and then pass on second attempt."""

    generated = _layout()
    mock_generate_layout.side_effect = [generated, generated]
    mock_snap_layout_to_grid.side_effect = [generated, generated]
    mock_validate_layout.side_effect = [
        _constraint_result(passed=False),
        _constraint_result(passed=True),
    ]

    result = generate_validated_layout(
        spatial_graph=_spatial_graph(), prompt="open-plan office"
    )

    assert result.success is True
    assert result.iterations_used == 2
    assert len(result.constraint_history) == 2
    assert mock_generate_layout.call_count == 2


@patch("app.services.generation_pipeline.validate_layout")
@patch("app.services.generation_pipeline.snap_layout_to_grid")
@patch("app.services.generation_pipeline.generate_layout")
def test_generate_validated_layout_max_iterations_exceeded(
    mock_generate_layout, mock_snap_layout_to_grid, mock_validate_layout
):
    """Always-invalid generations should fail after max iterations."""

    generated = _layout()
    mock_generate_layout.side_effect = [generated, generated, generated]
    mock_snap_layout_to_grid.side_effect = [generated, generated, generated]
    mock_validate_layout.side_effect = [
        _constraint_result(passed=False),
        _constraint_result(passed=False),
        _constraint_result(passed=False),
    ]

    result = generate_validated_layout(
        spatial_graph=_spatial_graph(), prompt="open-plan office", max_iterations=3
    )

    assert result.success is False
    assert result.iterations_used == 3
    assert result.layout is generated
    assert result.error_message == "Layout failed validation after 3 attempts"


@patch("app.services.generation_pipeline.validate_layout")
@patch("app.services.generation_pipeline.snap_layout_to_grid")
@patch("app.services.generation_pipeline.generate_layout")
def test_generate_validated_layout_feedback_prompt_contains_violations(
    mock_generate_layout, mock_snap_layout_to_grid, mock_validate_layout
):
    """Retry prompt should include explicit violation descriptions and affected ids."""

    generated = _layout()
    mock_generate_layout.side_effect = [generated, generated]
    mock_snap_layout_to_grid.side_effect = [generated, generated]
    mock_validate_layout.side_effect = [
        _constraint_result(passed=False),
        _constraint_result(passed=True),
    ]

    generate_validated_layout(spatial_graph=_spatial_graph(), prompt="dental clinic")

    retry_prompt = mock_generate_layout.call_args_list[1].kwargs["prompt"]
    assert "PREVIOUS ATTEMPT FAILED VALIDATION" in retry_prompt
    assert "Room A and Room B overlap by 2.30 sqm." in retry_prompt
    assert "affected: Room A, Room B" in retry_prompt


@patch("app.services.generation_pipeline._generate_validate_candidate")
def test_generate_validated_layout_parallel_candidates_selects_best(
    mock_generate_validate_candidate,
):
    """Parallel candidate mode should pick the best-scoring candidate."""

    def side_effect(_spatial_graph, prompt):
        if "CANDIDATE_VARIATION 1/2" in prompt:
            return _layout(), _constraint_result(passed=False)
        return _layout(), _constraint_result(passed=True)

    mock_generate_validate_candidate.side_effect = side_effect

    result = generate_validated_layout(
        spatial_graph=_spatial_graph(),
        prompt="open-plan office",
        parallel_candidates=2,
        max_workers=2,
    )

    assert result.success is True
    assert result.iterations_used == 1
    assert mock_generate_validate_candidate.call_count == 2

    prompts = [call.args[1] for call in mock_generate_validate_candidate.call_args_list]
    assert any("CANDIDATE_VARIATION 1/2" in prompt for prompt in prompts)
    assert any("CANDIDATE_VARIATION 2/2" in prompt for prompt in prompts)


# --- Adaptive candidate scheduling unit tests ---


def test_compute_adaptive_candidates_serial_mode_always_returns_one():
    """Serial mode (requested=1) should never adapt."""
    result = _compute_adaptive_candidates(
        requested_candidates=1,
        prior_constraint_result=_constraint_result(passed=False),
        prior_candidate_errors=2,
        prior_total_candidates=3,
        candidate_min=1,
        candidate_max=4,
    )
    assert result == 1


def test_compute_adaptive_candidates_reduces_on_provider_failures():
    """If prior generation failures occurred, reduce candidate count."""
    result = _compute_adaptive_candidates(
        requested_candidates=3,
        prior_constraint_result=_constraint_result(passed=False),
        prior_candidate_errors=1,  # one failure
        prior_total_candidates=3,
        candidate_min=1,
        candidate_max=4,
    )
    assert result == 2  # reduced by 1


def test_compute_adaptive_candidates_increases_on_warnings_only():
    """If best prior result had only warnings, increase candidate count."""
    result = _compute_adaptive_candidates(
        requested_candidates=2,
        prior_constraint_result=_warning_only_constraint_result(),
        prior_candidate_errors=0,
        prior_total_candidates=2,
        candidate_min=1,
        candidate_max=4,
    )
    assert result == 3  # increased by 1


def test_compute_adaptive_candidates_unchanged_on_blocking_errors():
    """If best prior result had blocking errors (no provider failures), keep count."""
    result = _compute_adaptive_candidates(
        requested_candidates=2,
        prior_constraint_result=_constraint_result(passed=False),  # has error violations
        prior_candidate_errors=0,
        prior_total_candidates=2,
        candidate_min=1,
        candidate_max=4,
    )
    assert result == 2  # unchanged


def test_compute_adaptive_candidates_clamped_to_min():
    """Candidate count should not drop below candidate_min."""
    result = _compute_adaptive_candidates(
        requested_candidates=2,
        prior_constraint_result=_constraint_result(passed=False),
        prior_candidate_errors=2,  # all failed
        prior_total_candidates=2,
        candidate_min=2,  # min is 2
        candidate_max=4,
    )
    assert result == 2  # clamped at min


def test_compute_adaptive_candidates_clamped_to_max():
    """Candidate count should not exceed candidate_max."""
    result = _compute_adaptive_candidates(
        requested_candidates=4,
        prior_constraint_result=_warning_only_constraint_result(),
        prior_candidate_errors=0,
        prior_total_candidates=4,
        candidate_min=1,
        candidate_max=4,  # max is 4
    )
    assert result == 4  # clamped at max


def test_compute_adaptive_candidates_first_iteration_uses_requested():
    """With no prior result, use requested value clamped to limits."""
    result = _compute_adaptive_candidates(
        requested_candidates=3,
        prior_constraint_result=None,
        prior_candidate_errors=0,
        prior_total_candidates=0,
        candidate_min=1,
        candidate_max=4,
    )
    assert result == 3


@patch("app.services.generation_pipeline._generate_validate_candidate")
def test_generate_validated_layout_serial_mode_deterministic(mock_generate_validate_candidate):
    """Serial mode (parallel_candidates=1) must stay at 1 regardless of results."""

    call_counts = []

    def side_effect(_spatial_graph, prompt):
        call_counts.append(prompt)
        # First iteration fails, second passes
        if len(call_counts) == 1:
            return _layout(), _constraint_result(passed=False)
        return _layout(), _constraint_result(passed=True)

    mock_generate_validate_candidate.side_effect = side_effect

    result = generate_validated_layout(
        spatial_graph=_spatial_graph(),
        prompt="office",
        parallel_candidates=1,
        max_workers=1,
        max_iterations=3,
    )

    assert result.success is True
    assert result.iterations_used == 2
    # Serial mode: no CANDIDATE_VARIATION hints in prompts
    assert all("CANDIDATE_VARIATION" not in p for p in call_counts)
