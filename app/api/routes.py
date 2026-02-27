"""API routes (Flask Blueprint)."""

import logging
import os
import tempfile
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from app.core.config import settings
from app.models.spatial import SpatialGraph
from app.services.bom_repository import create_bom, get_bom_by_floorplan
from app.services.floorplan_repository import (
    create_floorplan,
    get_floorplan_by_id,
    update_floorplan_error,
    update_floorplan_status,
    update_floorplan_vector_data,
)
from app.services.generation_pipeline import generate_validated_layout
from app.services.ingestion_pipeline import ingest_pdf

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


@api_bp.route("/ingest", methods=["POST"])
def ingest_floorplan():
    """
    Ingest a PDF floorplan, extract vectors, and detect structural walls.

    Creates a durable floorplan record with lifecycle status tracking.
    Returns a JSON containing the wall count, explicit geometry of wall
    segments, and the persistent `pdf_id` for downstream status polling.
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
        # Save uploaded file to temporary location
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

        try:
            # Mark processing state before running the pipeline
            if floorplan_id is not None:
                update_floorplan_status(floorplan_id, "processing")

            # Run ingestion pipeline
            result = ingest_pdf(tmp_path)

            # Persist the extraction result and mark as processed
            if floorplan_id is not None:
                wall_data = {
                    "total_wall_count": result.total_wall_count,
                    "total_linear_pts": result.total_linear_pts,
                    "source": result.source,
                    "wall_segments": [w.model_dump() for w in result.wall_segments],
                }
                update_floorplan_vector_data(floorplan_id, wall_data)
                update_floorplan_status(floorplan_id, "processed")

            response_data = result.model_dump()
            if floorplan_id is not None:
                response_data["pdf_id"] = floorplan_id
            return jsonify(response_data)

        except ValueError as e:
            # Catch ValueError when no vectors are found (e.g. scanned PDF)
            if floorplan_id is not None:
                update_floorplan_error(floorplan_id, str(e))
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            if floorplan_id is not None:
                update_floorplan_error(floorplan_id, f"Error processing PDF: {str(e)}")
            return jsonify({"error": f"Error processing PDF: {str(e)}"}), 500
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        return jsonify({"error": f"Error handling file upload: {str(e)}"}), 500


@api_bp.route("/status/<int:pdf_id>", methods=["GET"])
def get_pdf_status(pdf_id: int):
    """Get processing status of a floorplan by its persistent ID.

    Returns durable status details including lifecycle state, timestamps,
    and optional generation summary. Returns 404 for unknown IDs.
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

    return jsonify(response)


@api_bp.route("/generate", methods=["POST"])
def generate_layout_endpoint():
    """Generate and validate an interior layout from SpatialGraph + prompt.

    Optionally accepts a ``floorplan_id`` in the request body to persist
    generation result snapshots linked to the originating floorplan.
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

    try:
        spatial_graph = SpatialGraph.model_validate(spatial_graph_payload)
    except ValidationError as exc:
        return jsonify({"error": f"Invalid spatial_graph payload: {exc}"}), 400

    if not spatial_graph.walls:
        return jsonify({"error": "spatial_graph must include at least one wall"}), 400

    try:
        result = generate_validated_layout(
            spatial_graph=spatial_graph,
            prompt=prompt,
            parallel_candidates=parallel_candidates,
            max_workers=max_workers,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": f"Unexpected generation error: {exc}"}), 500

    latest_constraint_result = (
        result.constraint_history[-1].model_dump(mode="json")
        if result.constraint_history
        else {"passed": False, "violations": [], "summary": "0 errors, 0 warnings"}
    )
    response_body = {
        "success": result.success,
        "iterations_used": result.iterations_used,
        "layout": result.layout.to_json() if result.layout else None,
        "constraint_result": latest_constraint_result,
        "error_message": result.error_message,
    }

    # Persist generation result snapshot linked to the floorplan
    if floorplan_id is not None and result.success and result.layout is not None:
        try:
            bom_data = {
                "success": result.success,
                "iterations_used": result.iterations_used,
                "constraint_result": latest_constraint_result,
                "layout": result.layout.to_json(),
                "prompt": prompt,
            }
            bom_id = create_bom(
                floorplan_id=floorplan_id,
                total_cost_inr=0.0,  # Cost calculation is downstream; snapshot stored for provenance
                bom_data=bom_data,
            )
            response_body["bom_id"] = bom_id
        except Exception as persist_exc:
            # Persistence failure must not block the generation response
            logger.warning(
                "Could not persist generation result for floorplan %s: %s",
                floorplan_id,
                persist_exc,
            )

    status_code = 200 if result.success else 422

    return jsonify(response_body), status_code
