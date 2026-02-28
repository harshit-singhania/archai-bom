"""Business logic for the PDF ingestion flow (POST /api/v1/ingest).

The controller (routes.py) handles HTTP parsing and response serialisation.
This module owns everything in between: input validation, file persistence,
DB record creation, and job enqueuing.

Raises typed exceptions so the controller can map them to the right HTTP status
without any business logic leaking upward.
"""

import json
import logging
import tempfile
from dataclasses import dataclass
from typing import IO

from app.core.config import settings
from app.repositories.floorplan_repository import create_floorplan
from app.repositories.job_repository import create_job
from app.workers.queue_worker import enqueue_ingest_job

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed exceptions — controller maps these to HTTP status codes
# ---------------------------------------------------------------------------


class IngestValidationError(ValueError):
    """Raised when the incoming request is invalid (→ 400)."""


class IngestEnqueueError(RuntimeError):
    """Raised when the job cannot be created or enqueued (→ 500)."""


# ---------------------------------------------------------------------------
# Result dataclass returned to the controller
# ---------------------------------------------------------------------------


@dataclass
class IngestJobResult:
    job_id: int
    floorplan_id: int | None
    status_url: str


# ---------------------------------------------------------------------------
# Public service function
# ---------------------------------------------------------------------------


def enqueue_ingest(
    filename: str,
    file_stream: IO[bytes],
    project_id_raw: str | None,
) -> IngestJobResult:
    """Validate, persist, and enqueue a PDF ingestion job.

    Args:
        filename:       Original filename from the upload (used for validation
                        and as the pdf_storage_url in the DB record).
        file_stream:    Readable binary stream of the uploaded PDF.
        project_id_raw: Raw string value of the optional ``project_id`` form
                        field, or ``None`` if not provided.

    Returns:
        IngestJobResult with the job_id, optional floorplan_id, and status_url.

    Raises:
        IngestValidationError: filename is empty, not a PDF, or project_id
                               is not a valid integer.
        IngestEnqueueError:    Job could not be created or queued and the
                               caller should not retry silently.
    """
    # --- Input validation ---------------------------------------------------
    if not filename:
        raise IngestValidationError("No file selected")

    if not filename.endswith(".pdf"):
        raise IngestValidationError("File must be a PDF")

    project_id: int | None = None
    if project_id_raw is not None:
        try:
            project_id = int(project_id_raw)
        except (TypeError, ValueError):
            raise IngestValidationError("project_id must be an integer")

    # --- Persist file to a stable temp path the worker can read -------------
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode="wb") as tmp:
        file_stream.save(tmp)  # type: ignore[attr-defined]  # werkzeug FileStorage
        tmp_path = tmp.name

    # --- Create durable floorplan record (non-blocking on failure) ----------
    floorplan_id: int | None = None
    try:
        floorplan_id = create_floorplan(
            pdf_storage_url=filename,
            project_id=project_id,
            status="uploaded",
        )
    except Exception as db_exc:
        logger.warning("Could not persist floorplan record: %s", db_exc)

    # --- Build worker payload and enqueue -----------------------------------
    payload = json.dumps(
        {
            "pdf_path": tmp_path,
            "floorplan_id": floorplan_id,
        }
    )

    try:
        job_id = create_job(
            job_type="ingest",
            payload=payload,
            floorplan_id=floorplan_id,
        )
        enqueue_ingest_job(job_id)
    except Exception as queue_exc:
        logger.error("Could not enqueue ingest job: %s", queue_exc)
        raise IngestEnqueueError(f"Failed to enqueue job: {queue_exc}") from queue_exc

    return IngestJobResult(
        job_id=job_id,
        floorplan_id=floorplan_id,
        status_url=f"{settings.API_V1_PREFIX}/jobs/{job_id}",
    )
