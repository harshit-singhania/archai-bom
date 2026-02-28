"""Self-correcting generation pipeline for interior layouts."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging

from app.core.config import settings
from app.models.constraints import ConstraintResult
from app.models.generation import GenerationResult
from app.models.layout import GeneratedLayout
from app.models.spatial import SpatialGraph
from app.services.constraint_checker import validate_layout
from app.services.grid_snapper import snap_layout_to_grid
from app.integrations.layout_generator import generate_layout

logger = logging.getLogger(__name__)


def _format_constraint_feedback(constraint_result: ConstraintResult) -> tuple[str, str]:
    """Format violations into actionable feedback lines."""

    error_lines: list[str] = []
    warning_lines: list[str] = []
    for violation in constraint_result.violations:
        severity = violation.severity.upper()
        affected = ""
        if violation.affected_elements:
            affected = f" (affected: {', '.join(violation.affected_elements)})"
        line = f"- [{severity}] {violation.description}{affected}"

        if violation.severity == "error":
            error_lines.append(line)
        else:
            warning_lines.append(line)

    if not error_lines:
        error_lines = [
            "- [ERROR] Validation failed with no explicit blocking errors returned."
        ]

    return "\n".join(error_lines), "\n".join(warning_lines)


def _build_feedback_prompt(
    original_prompt: str,
    previous_layout: GeneratedLayout,
    constraint_result: ConstraintResult,
) -> str:
    """Build retry prompt with explicit constraint failure feedback."""

    formatted_errors, formatted_warnings = _format_constraint_feedback(
        constraint_result
    )
    previous_layout_json = json.dumps(previous_layout.to_json(), indent=2)

    warning_block = ""
    if formatted_warnings:
        warning_block = (
            "\nSecondary warnings to improve after fixing blocking errors:\n"
            f"{formatted_warnings}\n"
        )

    return (
        f"{original_prompt}\n\n"
        "PREVIOUS ATTEMPT FAILED VALIDATION.\n"
        "Previous generated layout JSON:\n"
        f"{previous_layout_json}\n\n"
        "Blocking errors to fix first:\n"
        f"{formatted_errors}\n"
        f"{warning_block}\n"
        "Regenerate the layout fixing these constraint violations. "
        "Keep all valid elements unchanged where possible. "
        "Return a full layout JSON and ensure no blocking [ERROR] violations remain."
    )


def _candidate_prompt(
    base_prompt: str, candidate_index: int, total_candidates: int
) -> str:
    """Create slight prompt variation for parallel candidate generation."""

    if total_candidates <= 1:
        return base_prompt

    variation_hints = [
        "Prioritize conflict-free door swings around interior walls.",
        "Prioritize fixture spacing to avoid overlaps while preserving circulation.",
        "Prefer sliding doors in tight spaces where swing clearance is hard.",
    ]
    hint = variation_hints[(candidate_index - 1) % len(variation_hints)]
    return (
        f"{base_prompt}\n\n"
        f"CANDIDATE_VARIATION {candidate_index}/{total_candidates}: {hint}"
    )


def _generate_validate_candidate(
    spatial_graph: SpatialGraph, prompt: str
) -> tuple[GeneratedLayout, ConstraintResult]:
    """Generate one candidate and immediately run snap + validation."""

    raw_layout = generate_layout(spatial_graph=spatial_graph, prompt=prompt)
    snapped_layout = snap_layout_to_grid(raw_layout)
    constraint_result = validate_layout(snapped_layout)
    return snapped_layout, constraint_result


def _constraint_score(constraint_result: ConstraintResult) -> tuple[int, int]:
    """Score constraints as (error_count, warning_count). Lower is better."""

    error_count = sum(
        1 for violation in constraint_result.violations if violation.severity == "error"
    )
    warning_count = len(constraint_result.violations) - error_count
    return error_count, warning_count


def _compute_adaptive_candidates(
    requested_candidates: int,
    prior_constraint_result: ConstraintResult | None,
    prior_candidate_errors: int,
    prior_total_candidates: int,
    candidate_min: int,
    candidate_max: int,
) -> int:
    """Adjust the number of parallel candidates for the next iteration.

    Adaptation rules (applied only when parallel mode is active, i.e. requested > 1):

    - If prior iteration had generation failures (provider errors) among candidates:
      reduce by 1 to cut cost pressure on the provider.
    - If prior iteration had only warnings (no blocking errors) from the best candidate:
      increase by 1 to cast a wider net.
    - Otherwise (blocking errors but no generation failures): keep current count.
    - Always clamp result to [candidate_min, candidate_max].

    When requested_candidates == 1 (serial mode), always return 1 — no adaptation.
    """

    if requested_candidates <= 1:
        return 1

    current = requested_candidates
    if prior_constraint_result is None:
        # First iteration — use requested value clamped to limits
        return max(candidate_min, min(candidate_max, current))

    prior_errors, prior_warnings = _constraint_score(prior_constraint_result)
    failure_rate = (
        prior_candidate_errors / prior_total_candidates
        if prior_total_candidates > 0
        else 0.0
    )

    if failure_rate > 0.0:
        # Provider errors occurred — reduce candidates to lower cost pressure
        adjusted = current - 1
        logger.info(
            "Adaptive fanout: reducing candidates from %d to %d (%.0f%% failure rate)",
            current,
            adjusted,
            failure_rate * 100,
        )
    elif prior_errors == 0 and prior_warnings > 0:
        # Only warnings — try more candidates to improve quality
        adjusted = current + 1
        logger.info(
            "Adaptive fanout: increasing candidates from %d to %d (warnings only, no errors)",
            current,
            adjusted,
        )
    else:
        # Blocking errors present — keep current count and rely on feedback prompt
        adjusted = current

    return max(candidate_min, min(candidate_max, adjusted))


def generate_validated_layout(
    spatial_graph: SpatialGraph,
    prompt: str,
    max_iterations: int = 3,
    parallel_candidates: int = 1,
    max_workers: int = 4,
) -> GenerationResult:
    """Generate, snap, validate, and retry layout generation up to max iterations.

    When parallel_candidates > 1, adaptive fanout adjusts the candidate count
    each iteration based on prior failure rates and violation severity, clamped
    to [settings.GENERATION_CANDIDATE_MIN, settings.GENERATION_CANDIDATE_MAX].
    Serial mode (parallel_candidates == 1) is always deterministic.
    """

    if max_iterations <= 0:
        raise ValueError("max_iterations must be at least 1")
    if parallel_candidates <= 0:
        raise ValueError("parallel_candidates must be at least 1")
    if max_workers <= 0:
        raise ValueError("max_workers must be at least 1")

    candidate_min = settings.GENERATION_CANDIDATE_MIN
    candidate_max = settings.GENERATION_CANDIDATE_MAX

    constraint_history: list[ConstraintResult] = []
    last_snapped_layout = None
    current_prompt = prompt
    current_candidates = parallel_candidates
    prior_constraint_result: ConstraintResult | None = None
    prior_candidate_errors: int = 0

    for iteration in range(1, max_iterations + 1):
        # Compute adaptive candidate count for this iteration
        current_candidates = _compute_adaptive_candidates(
            requested_candidates=current_candidates,
            prior_constraint_result=prior_constraint_result,
            prior_candidate_errors=prior_candidate_errors,
            prior_total_candidates=current_candidates,
            candidate_min=candidate_min,
            candidate_max=candidate_max,
        )

        candidate_prompts = [
            _candidate_prompt(current_prompt, index, current_candidates)
            for index in range(1, current_candidates + 1)
        ]

        candidate_outcomes: list[tuple[GeneratedLayout, ConstraintResult]] = []
        candidate_errors: list[Exception] = []

        if len(candidate_prompts) == 1:
            try:
                candidate_outcomes.append(
                    _generate_validate_candidate(spatial_graph, candidate_prompts[0])
                )
            except Exception as exc:  # pragma: no cover - explicit error path
                candidate_errors.append(exc)
        else:
            worker_count = min(max_workers, len(candidate_prompts))
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_to_prompt = {
                    executor.submit(
                        _generate_validate_candidate, spatial_graph, candidate_prompt
                    ): candidate_prompt
                    for candidate_prompt in candidate_prompts
                }
                for future in as_completed(future_to_prompt):
                    try:
                        candidate_outcomes.append(future.result())
                    except Exception as exc:
                        candidate_errors.append(exc)

        if not candidate_outcomes:
            first_error = (
                candidate_errors[0]
                if candidate_errors
                else RuntimeError("No candidates produced")
            )
            raise RuntimeError(
                f"All generation candidates failed: {first_error}"
            ) from first_error

        snapped_layout, constraint_result = min(
            candidate_outcomes,
            key=lambda outcome: _constraint_score(outcome[1]),
        )

        constraint_history.append(constraint_result)
        last_snapped_layout = snapped_layout

        # Track signals for next iteration's adaptive decision
        prior_constraint_result = constraint_result
        prior_candidate_errors = len(candidate_errors)

        if constraint_result.passed:
            return GenerationResult(
                layout=snapped_layout,
                success=True,
                iterations_used=iteration,
                constraint_history=constraint_history,
                error_message=None,
            )

        current_prompt = _build_feedback_prompt(
            prompt, snapped_layout, constraint_result
        )

    return GenerationResult(
        layout=last_snapped_layout,
        success=False,
        iterations_used=max_iterations,
        constraint_history=constraint_history,
        error_message=f"Layout failed validation after {max_iterations} attempts",
    )
