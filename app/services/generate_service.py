"""Business logic for the layout generation flow (POST /api/v1/generate).

The controller (routes.py) handles HTTP parsing and response serialisation.
This module owns everything in between: input validation, spatial-graph
validation, job payload construction, and job enqueuing.

Raises typed exceptions so the controller can map them to the right HTTP status
without any business logic leaking upward.
"""

import json
import logging
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.config import settings
from app.models.spatial import SpatialGraph
from app.repositories.job_repository import create_job
from app.workers.queue_worker import enqueue_generate_job

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed exceptions — controller maps these to HTTP status codes
# ---------------------------------------------------------------------------


class GenerateValidationError(ValueError):
    """Raised when the incoming request payload is invalid (→ 400)."""


class GenerateEnqueueError(RuntimeError):
    """Raised when the job cannot be created or enqueued (→ 500)."""


# ---------------------------------------------------------------------------
# Result dataclass returned to the controller
# ---------------------------------------------------------------------------


@dataclass
class GenerateJobResult:
    job_id: int
    status_url: str


# ---------------------------------------------------------------------------
# Public service function
# ---------------------------------------------------------------------------


def enqueue_generate(
    spatial_graph_payload: dict | None,
    prompt: str | None,
    floorplan_id: int | None,
    parallel_candidates_raw: int | None,
    max_workers_raw: int | None,
) -> GenerateJobResult:
    """Validate a generation request and enqueue a background generate job.

    Args:
        spatial_graph_payload:  Raw dict from the JSON body (may be ``None``).
        prompt:                 Generation prompt string (may be ``None``).
        floorplan_id:           Optional DB floorplan to link results against.
        parallel_candidates_raw: Requested concurrency level, or ``None`` to
                                 use the server default.
        max_workers_raw:        Max worker threads, or ``None`` to use default.

    Returns:
        GenerateJobResult with the job_id and status_url.

    Raises:
        GenerateValidationError: Any required field is missing/invalid, or the
                                 spatial_graph fails model validation (→ 400).
        GenerateEnqueueError:    Job creation or enqueue failed (→ 500).
    """
    # --- Required field presence --------------------------------------------
    if spatial_graph_payload is None:
        raise GenerateValidationError("spatial_graph is required")

    if not isinstance(prompt, str) or not prompt.strip():
        raise GenerateValidationError("prompt must be a non-empty string")

    # --- Concurrency parameters ---------------------------------------------
    parallel_candidates = (
        parallel_candidates_raw
        if parallel_candidates_raw is not None
        else settings.GENERATION_PARALLEL_CANDIDATES
    )
    max_workers = (
        max_workers_raw
        if max_workers_raw is not None
        else settings.GENERATION_MAX_WORKERS
    )

    if not isinstance(parallel_candidates, int) or parallel_candidates <= 0:
        raise GenerateValidationError("parallel_candidates must be a positive integer")

    if not isinstance(max_workers, int) or max_workers <= 0:
        raise GenerateValidationError("max_workers must be a positive integer")

    # --- Optional floorplan linkage -----------------------------------------
    if floorplan_id is not None and not isinstance(floorplan_id, int):
        raise GenerateValidationError("floorplan_id must be an integer")

    # --- Spatial-graph model validation (fast, no network) ------------------
    try:
        spatial_graph = SpatialGraph.model_validate(spatial_graph_payload)
    except ValidationError as exc:
        raise GenerateValidationError(f"Invalid spatial_graph payload: {exc}") from exc

    if not spatial_graph.walls:
        raise GenerateValidationError("spatial_graph must include at least one wall")

    # --- Serialise worker payload and enqueue --------------------------------
    job_payload = json.dumps(
        {
            "spatial_graph": spatial_graph_payload,
            "prompt": prompt,
            "floorplan_id": floorplan_id,
            "parallel_candidates": parallel_candidates,
            "max_workers": max_workers,
        }
    )

    try:
        job_id = create_job(
            job_type="generate",
            payload=job_payload,
            floorplan_id=floorplan_id,
        )
        enqueue_generate_job(job_id)
    except Exception as queue_exc:
        logger.error("Could not enqueue generate job: %s", queue_exc)
        raise GenerateEnqueueError(f"Failed to enqueue job: {queue_exc}") from queue_exc

    return GenerateJobResult(
        job_id=job_id,
        status_url=f"{settings.API_V1_PREFIX}/jobs/{job_id}",
    )
