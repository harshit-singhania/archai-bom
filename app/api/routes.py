"""API routes (Flask Blueprint) — async enqueue model.

All heavy workloads (PDF ingestion, layout generation) are now delegated to
background queue workers. Endpoints return 202 Accepted immediately with a
job_id and a status_url for polling.

Backward-compatible fields are preserved where feasible. The status endpoint
continues to serve floorplan lifecycle details alongside async job state.
"""

import json
import logging
import os
import tempfile
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from app.core.config import settings
from app.models.spatial import SpatialGraph
from app.services.bom_repository import get_bom_by_floorplan
from app.services.floorplan_repository import (
    create_floorplan,
    get_floorplan_by_id,
)
from app.services.job_repository import (
    create_job,
    get_job_by_id,
    list_jobs_by_floorplan,
)
from app.workers.queue_worker import enqueue_ingest_job, enqueue_generate_job

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


# ---------------------------------------------------------------------------
# POST /ingest — enqueue PDF ingestion
# ---------------------------------------------------------------------------


@api_bp.route("/ingest", methods=["POST"])
def ingest_floorplan():
    """Accept a PDF upload and enqueue an ingestion job.

    Returns 202 Accepted immediately with a ``job_id`` and ``status_url``
    for polling job progress. The heavy PDF extraction runs in the background
    worker.

    Request (multipart/form-data):
      - file: PDF file (required)
      - project_id: integer (optional)

    Response 202:
      {
        "job_id": <int>,
        "status": "queued",
        "status_url": "/api/v1/jobs/<job_id>",
        "pdf_id": <int>         # floorplan DB record (for backward compat)
      }
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400

    # Optional project linkage from form data
    project_id = request.form.get("project_id")
    if project_id is not None:
        try:
            project_id = int(project_id)
        except (TypeError, ValueError):
            return jsonify({"error": "project_id must be an integer"}), 400

    try:
        # Persist the file to a stable temp path the worker can access
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode="wb") as tmp:
            file.save(tmp)
            tmp_path = tmp.name

        # Create a durable floorplan record immediately on upload
        try:
            floorplan_id = create_floorplan(
                pdf_storage_url=file.filename,
                project_id=project_id,
                status="uploaded",
            )
        except Exception as db_exc:
            logger.warning("Could not persist floorplan record: %s", db_exc)
            floorplan_id = None

        # Build the job payload for the worker
        payload = json.dumps({
            "pdf_path": tmp_path,
            "floorplan_id": floorplan_id,
        })

        # Create AsyncJob record and enqueue for background execution
        try:
            job_id = create_job(
                job_type="ingest",
                payload=payload,
                floorplan_id=floorplan_id,
            )
            enqueue_ingest_job(job_id)
        except Exception as queue_exc:
            logger.warning("Could not enqueue ingest job: %s", queue_exc)
            # If queueing fails, still return a job_id if we created it
            # (worker will pick it up later or caller can retry)
            if "job_id" not in dir():
                return jsonify({"error": f"Failed to enqueue job: {queue_exc}"}), 500

        response_data = {
            "job_id": job_id,
            "status": "queued",
            "status_url": f"{settings.API_V1_PREFIX}/jobs/{job_id}",
        }
        if floorplan_id is not None:
            response_data["pdf_id"] = floorplan_id

        return jsonify(response_data), 202

    except Exception as e:
        return jsonify({"error": f"Error handling file upload: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# GET /status/<pdf_id> — floorplan lifecycle status (backward-compatible)
# ---------------------------------------------------------------------------


@api_bp.route("/status/<int:pdf_id>", methods=["GET"])
def get_pdf_status(pdf_id: int):
    """Get processing status of a floorplan by its persistent ID.

    Returns durable status details including lifecycle state, timestamps,
    and optional generation summary. Returns 404 for unknown IDs.

    Also includes a ``jobs`` list with the async job states linked to this
    floorplan for callers that prefer polling the job-level view.
    """
    floorplan = get_floorplan_by_id(pdf_id)
    if floorplan is None:
        return jsonify({"error": f"Floorplan {pdf_id} not found"}), 404

    response = {
        "pdf_id": floorplan["id"],
        "status": floorplan["status"],
        "created_at": floorplan.get("created_at"),
        "updated_at": floorplan.get("updated_at"),
        "error_message": floorplan.get("error_message"),
    }

    # Attach latest generation summary if available
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

    # Include async job list for pollers preferring job-level view
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

    return jsonify(response)


# ---------------------------------------------------------------------------
# GET /jobs/<job_id> — async job status endpoint
# ---------------------------------------------------------------------------


@api_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job_status(job_id: int):
    """Poll the status of an async job by its ID.

    Returns the full job record including status, result_ref (on success),
    and error_message (on failure).

    Response fields:
      - job_id, job_type, status (queued|running|succeeded|failed)
      - result_ref: dict with result_type, result_id etc. (on success)
      - error_message: string (on failure)
      - created_at, started_at, finished_at: ISO timestamps
    """
    job = get_job_by_id(job_id)
    if job is None:
        return jsonify({"error": f"Job {job_id} not found"}), 404

    return jsonify({
        "job_id": job["id"],
        "job_type": job["job_type"],
        "status": job["status"],
        "result_ref": job.get("result_ref"),
        "error_message": job.get("error_message"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
    })


# ---------------------------------------------------------------------------
# POST /generate — enqueue layout generation
# ---------------------------------------------------------------------------


@api_bp.route("/generate", methods=["POST"])
def generate_layout_endpoint():
    """Accept a generation request and enqueue a generate job.

    Returns 202 Accepted immediately with a ``job_id`` and ``status_url``
    for polling. The heavy layout generation runs in the background worker.

    Request (JSON):
      - spatial_graph (object, required)
      - prompt (str, required)
      - floorplan_id (int, optional)
      - parallel_candidates (int, optional)
      - max_workers (int, optional)

    Response 202:
      {
        "job_id": <int>,
        "status": "queued",
        "status_url": "/api/v1/jobs/<job_id>"
      }
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    spatial_graph_payload = payload.get("spatial_graph")
    prompt = payload.get("prompt")

    if spatial_graph_payload is None:
        return jsonify({"error": "spatial_graph is required"}), 400
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "prompt must be a non-empty string"}), 400

    parallel_candidates = payload.get(
        "parallel_candidates", settings.GENERATION_PARALLEL_CANDIDATES
    )
    max_workers = payload.get("max_workers", settings.GENERATION_MAX_WORKERS)

    if not isinstance(parallel_candidates, int) or parallel_candidates <= 0:
        return jsonify({"error": "parallel_candidates must be a positive integer"}), 400
    if not isinstance(max_workers, int) or max_workers <= 0:
        return jsonify({"error": "max_workers must be a positive integer"}), 400

    # Optional floorplan linkage for persistence
    floorplan_id = payload.get("floorplan_id")
    if floorplan_id is not None and not isinstance(floorplan_id, int):
        return jsonify({"error": "floorplan_id must be an integer"}), 400

    # Validate spatial_graph shape before enqueuing (fast, no network)
    try:
        spatial_graph = SpatialGraph.model_validate(spatial_graph_payload)
    except ValidationError as exc:
        return jsonify({"error": f"Invalid spatial_graph payload: {exc}"}), 400

    if not spatial_graph.walls:
        return jsonify({"error": "spatial_graph must include at least one wall"}), 400

    # Serialise full payload for the worker
    job_payload = json.dumps({
        "spatial_graph": spatial_graph_payload,
        "prompt": prompt,
        "floorplan_id": floorplan_id,
        "parallel_candidates": parallel_candidates,
        "max_workers": max_workers,
    })

    try:
        job_id = create_job(
            job_type="generate",
            payload=job_payload,
            floorplan_id=floorplan_id,
        )
        enqueue_generate_job(job_id)
    except Exception as queue_exc:
        logger.error("Could not enqueue generate job: %s", queue_exc)
        return jsonify({"error": f"Failed to enqueue job: {queue_exc}"}), 500

    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "status_url": f"{settings.API_V1_PREFIX}/jobs/{job_id}",
    }), 202
