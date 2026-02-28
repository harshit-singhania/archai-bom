"""API routes (Flask Blueprint) — thin controller layer.

Responsibilities of this module:
  - Parse HTTP requests (files, form data, JSON body)
  - Delegate ALL business logic to dedicated service modules
  - Map service exceptions to HTTP status codes
  - Serialise service results to JSON responses

Business logic lives in:
  app/services/ingest_service.py   → POST /ingest
  app/services/generate_service.py → POST /generate
  app/services/status_service.py   → GET /status/<pdf_id>, GET /jobs/<job_id>
"""

import logging

from flask import Blueprint, jsonify, request

from app.services.generate_service import (
    GenerateEnqueueError,
    GenerateValidationError,
    enqueue_generate,
)
from app.services.ingest_service import (
    IngestEnqueueError,
    IngestValidationError,
    enqueue_ingest,
)
from app.services.status_service import (
    FloorplanNotFoundError,
    JobNotFoundError,
    get_floorplan_status,
    get_job_status,
)

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
        "pdf_id": <int>   # floorplan DB record (for backward compat)
      }
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    try:
        result = enqueue_ingest(
            filename=file.filename or "",
            file_stream=file,
            project_id_raw=request.form.get("project_id"),
        )
    except IngestValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except IngestEnqueueError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        logger.exception("Unexpected error during ingest")
        return jsonify({"error": f"Error handling file upload: {exc}"}), 500

    response_data: dict = {
        "job_id": result.job_id,
        "status": "queued",
        "status_url": result.status_url,
    }
    if result.floorplan_id is not None:
        response_data["pdf_id"] = result.floorplan_id

    return jsonify(response_data), 202


# ---------------------------------------------------------------------------
# GET /status/<pdf_id> — floorplan lifecycle status (backward-compatible)
# ---------------------------------------------------------------------------


@api_bp.route("/status/<int:pdf_id>", methods=["GET"])
def get_pdf_status(pdf_id: int):
    """Get processing status of a floorplan by its persistent ID.

    Returns durable status details including lifecycle state, timestamps,
    optional generation summary, and linked async jobs. Returns 404 for
    unknown IDs.
    """
    try:
        data = get_floorplan_status(pdf_id)
    except FloorplanNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(data)


# ---------------------------------------------------------------------------
# GET /jobs/<job_id> — async job status endpoint
# ---------------------------------------------------------------------------


@api_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job_status_endpoint(job_id: int):
    """Poll the status of an async job by its ID.

    Returns the full job record including status, result_ref (on success),
    and error_message (on failure).

    Response fields:
      - job_id, job_type, status (queued|running|succeeded|failed)
      - result_ref: dict with result_type, result_id etc. (on success)
      - error_message: string (on failure)
      - created_at, started_at, finished_at: ISO timestamps
    """
    try:
        data = get_job_status(job_id)
    except JobNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(data)


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
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    try:
        result = enqueue_generate(
            spatial_graph_payload=body.get("spatial_graph"),
            prompt=body.get("prompt"),
            floorplan_id=body.get("floorplan_id"),
            parallel_candidates_raw=body.get("parallel_candidates"),
            max_workers_raw=body.get("max_workers"),
        )
    except GenerateValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except GenerateEnqueueError as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(
        {
            "job_id": result.job_id,
            "status": "queued",
            "status_url": result.status_url,
        }
    ), 202
