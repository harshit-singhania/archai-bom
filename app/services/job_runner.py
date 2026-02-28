"""Job runner: executes queued ingest and generate jobs, persists outcomes.

run_job() is the single entry point called by the queue worker.
It is intentionally synchronous so it can run in a standard thread pool
and be tested without a live queue/Redis connection.

Lifecycle:
  1. Load job from DB, mark as running.
  2. Deserialise payload and dispatch to the correct handler.
  3. On success -> mark_job_succeeded with result_ref.
  4. On any exception -> mark_job_failed with error_message.
"""

import json
import logging
from typing import Any, Dict, Optional

from app.services.ingestion_pipeline import ingest_pdf
from app.services.floorplan_repository import (
    update_floorplan_error,
    update_floorplan_status,
    update_floorplan_vector_data,
)
from app.services.job_repository import (
    get_job_by_id,
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_job(job_id: int) -> None:
    """Execute a queued async job and persist the outcome to the database.

    This function is designed to be called from a queue worker process. It
    handles its own status transitions and must not raise — all exceptions
    are caught and persisted as failed states so the queue worker stays alive.

    Args:
        job_id: Primary key of the AsyncJob record to execute.
    """
    job = get_job_by_id(job_id)
    if job is None:
        logger.error("run_job called with unknown job_id=%s", job_id)
        return

    # Transition to running before any work starts
    mark_job_running(job_id)
    logger.info("Starting job %s (type=%s)", job_id, job["job_type"])

    try:
        if job["job_type"] == "ingest":
            result_ref = _run_ingest_job(job)
        elif job["job_type"] == "generate":
            result_ref = _run_generate_job(job)
        else:
            raise ValueError(f"Unknown job_type '{job['job_type']}'")

        mark_job_succeeded(job_id, result_ref=result_ref)
        logger.info("Job %s succeeded (type=%s)", job_id, job["job_type"])

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        mark_job_failed(job_id, error_message=error_message)
        logger.error(
            "Job %s failed (type=%s): %s", job_id, job["job_type"], error_message
        )


# ---------------------------------------------------------------------------
# Job handlers
# ---------------------------------------------------------------------------


def _run_ingest_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an ingest job and return a result_ref dict.

    Expected payload keys:
      - pdf_path (str): Absolute path to the temporary PDF file.
      - floorplan_id (int, optional): Existing floorplan DB record to update.

    Returns:
        result_ref dict with result_type="floorplan" and result_id.
    """
    payload = _parse_payload(job)
    pdf_path = payload["pdf_path"]
    floorplan_id: Optional[int] = payload.get("floorplan_id")

    if floorplan_id is not None:
        update_floorplan_status(floorplan_id, "processing")

    try:
        result = ingest_pdf(pdf_path)
    except Exception:
        if floorplan_id is not None:
            update_floorplan_error(
                floorplan_id, "Ingestion failed in background worker"
            )
        raise

    if floorplan_id is not None:
        wall_data = {
            "total_wall_count": result.total_wall_count,
            "total_linear_pts": result.total_linear_pts,
            "source": result.source,
            "wall_segments": [w.model_dump() for w in result.wall_segments],
        }
        update_floorplan_vector_data(floorplan_id, wall_data)
        update_floorplan_status(floorplan_id, "processed")

    result_ref: Dict[str, Any] = {
        "result_type": "floorplan",
        "total_wall_count": result.total_wall_count,
        "source": result.source,
    }
    if floorplan_id is not None:
        result_ref["result_id"] = floorplan_id

    return result_ref


def _run_generate_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a generation job and return a result_ref dict.

    Expected payload keys:
      - spatial_graph (dict): Serialised SpatialGraph.
      - prompt (str): Generation prompt.
      - floorplan_id (int, optional): Floorplan to link the BOM to.
      - parallel_candidates (int, optional): Candidate count override.
      - max_workers (int, optional): Worker count override.

    Returns:
        result_ref dict with result_type="bom" and optional result_id.
    """
    from app.core.config import settings
    from app.models.bom import MaterialInfo
    from app.models.spatial import SpatialGraph
    from app.services.bom_calculator import calculate_bom
    from app.services.generation_pipeline import generate_validated_layout
    from app.services.bom_repository import create_bom
    from app.services.materials_repository import get_all_materials

    payload = _parse_payload(job)
    spatial_graph_data = payload["spatial_graph"]
    prompt: str = payload["prompt"]
    floorplan_id: Optional[int] = payload.get("floorplan_id")
    parallel_candidates: int = int(
        payload.get("parallel_candidates", settings.GENERATION_PARALLEL_CANDIDATES)
    )
    max_workers: int = int(payload.get("max_workers", settings.GENERATION_MAX_WORKERS))

    spatial_graph = SpatialGraph.model_validate(spatial_graph_data)
    result = generate_validated_layout(
        spatial_graph=spatial_graph,
        prompt=prompt,
        parallel_candidates=parallel_candidates,
        max_workers=max_workers,
    )

    result_ref: Dict[str, Any] = {
        "result_type": "bom",
        "success": result.success,
        "iterations_used": result.iterations_used,
    }

    if result.success and result.layout is not None and floorplan_id is not None:
        latest_constraint = (
            result.constraint_history[-1].model_dump(mode="json")
            if result.constraint_history
            else {"passed": False, "violations": [], "summary": "0 errors, 0 warnings"}
        )
        bom_data = {
            "success": result.success,
            "iterations_used": result.iterations_used,
            "constraint_result": latest_constraint,
            "layout": result.layout.to_json(),
            "prompt": prompt,
        }

        total_cost = 0.0
        try:
            raw_materials = get_all_materials()
            materials = [MaterialInfo(**material) for material in raw_materials]
            bom_result = calculate_bom(layout=result.layout, materials=materials)
            total_cost = bom_result.grand_total_inr
            bom_data["line_items"] = [
                item.model_dump(mode="json") for item in bom_result.line_items
            ]
            bom_data["room_count"] = bom_result.room_count
            bom_data["total_area_sqm"] = bom_result.total_area_sqm
        except Exception as calc_exc:
            logger.warning(
                "BOM calculation failed, storing layout without pricing: %s",
                calc_exc,
            )

        try:
            bom_id = create_bom(
                floorplan_id=floorplan_id,
                total_cost_inr=total_cost,
                bom_data=bom_data,
            )
            result_ref["result_id"] = bom_id
        except Exception as persist_exc:
            logger.warning(
                "Could not persist BOM for floorplan %s in background job: %s",
                floorplan_id,
                persist_exc,
            )

    if not result.success:
        raise RuntimeError(
            result.error_message or "Generation pipeline did not produce a valid layout"
        )

    return result_ref


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    """Deserialise the JSON payload string from the job record.

    Args:
        job: Serialised job dict from get_job_by_id.

    Returns:
        Payload as a Python dict.

    Raises:
        ValueError: If payload is missing or not valid JSON.
    """
    raw = job.get("payload")
    if not raw:
        raise ValueError(f"Job {job['id']} has no payload")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Job {job['id']} payload is not valid JSON: {exc}") from exc
