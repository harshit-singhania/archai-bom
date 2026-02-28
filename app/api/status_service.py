"""Business logic for floorplan status and async job status queries.

Covers:
  GET /api/v1/status/<pdf_id>  — floorplan lifecycle view
  GET /api/v1/jobs/<job_id>    — async job polling view

The controller (routes.py) handles HTTP parsing and response serialisation.
This module assembles the response dicts and raises typed exceptions on lookup
failures so the controller can map them to the correct HTTP status codes.
"""

import logging
from typing import Any

from app.services.bom_repository import get_bom_by_floorplan
from app.services.floorplan_repository import get_floorplan_by_id
from app.services.job_repository import get_job_by_id, list_jobs_by_floorplan

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed exceptions — controller maps these to HTTP status codes
# ---------------------------------------------------------------------------


class FloorplanNotFoundError(LookupError):
    """Raised when the requested floorplan does not exist (→ 404)."""


class JobNotFoundError(LookupError):
    """Raised when the requested async job does not exist (→ 404)."""


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


def get_floorplan_status(pdf_id: int) -> dict[str, Any]:
    """Assemble the full status response dict for a floorplan.

    Args:
        pdf_id: Persistent floorplan record ID.

    Returns:
        Dict with keys: pdf_id, status, created_at, updated_at, error_message,
        generation_summary (dict | None), jobs (list[dict]).

    Raises:
        FloorplanNotFoundError: No floorplan exists with this ID (→ 404).
    """
    floorplan = get_floorplan_by_id(pdf_id)
    if floorplan is None:
        raise FloorplanNotFoundError(f"Floorplan {pdf_id} not found")

    response: dict[str, Any] = {
        "pdf_id": floorplan["id"],
        "status": floorplan["status"],
        "created_at": floorplan.get("created_at"),
        "updated_at": floorplan.get("updated_at"),
        "error_message": floorplan.get("error_message"),
    }

    # Attach latest BOM/generation summary (non-blocking on failure)
    try:
        bom = get_bom_by_floorplan(pdf_id)
        if bom:
            response["generation_summary"] = {
                "bom_id": bom["id"],
                "total_cost_inr": bom["total_cost_inr"],
                "generated_at": bom.get("created_at"),
            }
        else:
            response["generation_summary"] = None
    except Exception as bom_exc:
        logger.warning("Could not fetch BOM for floorplan %s: %s", pdf_id, bom_exc)
        response["generation_summary"] = None

    # Attach linked async jobs for callers that prefer job-level polling
    try:
        jobs = list_jobs_by_floorplan(pdf_id)
        response["jobs"] = [
            {
                "job_id": j["id"],
                "job_type": j["job_type"],
                "status": j["status"],
                "created_at": j["created_at"],
                "finished_at": j["finished_at"],
            }
            for j in jobs
        ]
    except Exception as jobs_exc:
        logger.warning("Could not fetch jobs for floorplan %s: %s", pdf_id, jobs_exc)
        response["jobs"] = []

    return response


def get_job_status(job_id: int) -> dict[str, Any]:
    """Assemble the full status response dict for an async job.

    Args:
        job_id: Async job record ID.

    Returns:
        Dict with keys: job_id, job_type, status, result_ref, error_message,
        created_at, updated_at, started_at, finished_at.

    Raises:
        JobNotFoundError: No job exists with this ID (→ 404).
    """
    job = get_job_by_id(job_id)
    if job is None:
        raise JobNotFoundError(f"Job {job_id} not found")

    return {
        "job_id": job["id"],
        "job_type": job["job_type"],
        "status": job["status"],
        "result_ref": job.get("result_ref"),
        "error_message": job.get("error_message"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
    }
