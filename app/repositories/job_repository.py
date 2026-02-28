"""Async job repository for lifecycle management of queue jobs.

Provides create/read/update helpers for AsyncJob records. All functions
return typed dicts to maintain a clean boundary between the persistence
layer and service/worker callers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlmodel import select

from app.core.database import get_session
from app.models.database import AsyncJob

# ---------------------------------------------------------------------------
# Valid job statuses
# ---------------------------------------------------------------------------

VALID_JOB_TYPES = frozenset({"ingest", "generate"})
VALID_STATUSES = frozenset({"queued", "running", "succeeded", "failed"})


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


def create_job(
    job_type: str,
    payload: Optional[str] = None,
    floorplan_id: Optional[int] = None,
) -> int:
    """Create a new async job record in queued state.

    Args:
        job_type: One of "ingest" or "generate".
        payload: JSON-serialised job arguments for cross-process portability.
        floorplan_id: Optional reference to the originating floorplan.

    Returns:
        Created AsyncJob.id (integer primary key).

    Raises:
        ValueError: If job_type is not a recognised type.
    """
    if job_type not in VALID_JOB_TYPES:
        raise ValueError(f"Unknown job_type '{job_type}'. Must be one of {sorted(VALID_JOB_TYPES)}.")

    with get_session() as session:
        job = AsyncJob(
            job_type=job_type,
            status="queued",
            payload=payload,
            floorplan_id=floorplan_id,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single async job by primary key.

    Args:
        job_id: AsyncJob primary key.

    Returns:
        Serialised job dict or None when not found.
    """
    with get_session() as session:
        job = session.get(AsyncJob, job_id)
        if job is None:
            return None
        return _serialise_job(job)


def list_jobs_by_floorplan(floorplan_id: int) -> List[Dict[str, Any]]:
    """List all async jobs linked to a specific floorplan.

    Args:
        floorplan_id: Floorplan primary key to filter by.

    Returns:
        List of serialised job dicts, newest-first.
    """
    with get_session() as session:
        query = (
            select(AsyncJob)
            .where(AsyncJob.floorplan_id == floorplan_id)
            .order_by(AsyncJob.created_at.desc())
        )
        jobs = session.exec(query).all()
        return [_serialise_job(j) for j in jobs]


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


def mark_job_running(job_id: int) -> bool:
    """Transition a job from queued to running and record start time.

    Args:
        job_id: AsyncJob primary key.

    Returns:
        True if updated, False if job not found.
    """
    with get_session() as session:
        job = session.get(AsyncJob, job_id)
        if job is None:
            return False
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        session.add(job)
        session.commit()
        return True


def mark_job_succeeded(
    job_id: int,
    result_ref: Optional[Dict[str, Any]] = None,
) -> bool:
    """Transition a job to succeeded and store optional result references.

    Args:
        job_id: AsyncJob primary key.
        result_ref: Dict with result_type and result_id for downstream fetch.

    Returns:
        True if updated, False if job not found.
    """
    with get_session() as session:
        job = session.get(AsyncJob, job_id)
        if job is None:
            return False
        job.status = "succeeded"
        job.result_ref = result_ref or {}
        job.finished_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        session.add(job)
        session.commit()
        return True


def mark_job_failed(job_id: int, error_message: str) -> bool:
    """Transition a job to failed and record the error message.

    Args:
        job_id: AsyncJob primary key.
        error_message: Human-readable description of the failure.

    Returns:
        True if updated, False if job not found.
    """
    with get_session() as session:
        job = session.get(AsyncJob, job_id)
        if job is None:
            return False
        job.status = "failed"
        job.error_message = error_message
        job.finished_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        session.add(job)
        session.commit()
        return True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _serialise_job(job: AsyncJob) -> Dict[str, Any]:
    """Convert an AsyncJob ORM object to a plain dict."""
    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "floorplan_id": job.floorplan_id,
        "payload": job.payload,
        "error_message": job.error_message,
        "result_ref": job.result_ref,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
