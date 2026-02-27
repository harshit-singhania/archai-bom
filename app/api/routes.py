"""API routes (Flask Blueprint)."""

import os
import tempfile
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from app.core.config import settings
from app.models.spatial import SpatialGraph
from app.services.generation_pipeline import generate_validated_layout
from app.services.ingestion_pipeline import ingest_pdf

api_bp = Blueprint("api", __name__)


@api_bp.route("/ingest", methods=["POST"])
def ingest_floorplan():
    """
    Ingest a PDF floorplan, extract vectors, and detect structural walls.

    Returns a JSON containing the wall count and explicit geometry
    of wall segments.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400

    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode="wb") as tmp:
            file.save(tmp)
            tmp_path = tmp.name

        try:
            # Run ingestion pipeline
            result = ingest_pdf(tmp_path)
            return jsonify(result.model_dump())

        except ValueError as e:
            # Catch ValueError when no vectors are found (e.g. scanned PDF)
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Error processing PDF: {str(e)}"}), 500
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        return jsonify({"error": f"Error handling file upload: {str(e)}"}), 500


@api_bp.route("/status/<pdf_id>", methods=["GET"])
def get_pdf_status(pdf_id: str):
    """Get processing status of a PDF."""
    return jsonify({"pdf_id": pdf_id, "status": "placeholder"})


@api_bp.route("/generate", methods=["POST"])
def generate_layout_endpoint():
    """Generate and validate an interior layout from SpatialGraph + prompt."""

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
    status_code = 200 if result.success else 422

    return jsonify(response_body), status_code
