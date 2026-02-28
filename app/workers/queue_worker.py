"""Queue worker entrypoint for async job execution.

This module provides:
  - enqueue_job(): called from API routes to enqueue a job into Redis/RQ.
  - start_worker(): blocking worker loop that listens for and executes jobs.

Architecture notes:
  - RQ (Redis Queue) is used as the queue backend. It requires a running
    Redis instance reachable at settings.REDIS_URL.
  - The worker calls app.services.job_runner.run_job(job_id) for each
    dequeued job. run_job handles all DB lifecycle transitions internally.
  - Retry/backoff: RQ's built-in retry with exponential backoff is used
    for transient worker failures. Non-transient failures (marked failed
    in DB) are NOT retried.

Usage:
    # Enqueue from API process
    from app.workers.queue_worker import enqueue_job
    job_id = enqueue_job(db_job_id)

    # Start the worker (blocking — run in a separate process/container)
    python -m app.workers.queue_worker
"""

import logging
import sys
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Queue client (lazy initialisation to avoid import-time Redis connections)
# ---------------------------------------------------------------------------


def _get_redis_connection():
    """Create a Redis connection from settings.REDIS_URL.

    Raises:
        ImportError: When redis package is not installed.
        redis.exceptions.ConnectionError: When Redis is unreachable.
    """
    try:
        import redis  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "redis package is required for the queue worker. "
            "Install it with: pip install redis rq"
        ) from exc

    return redis.from_url(settings.REDIS_URL)


def _get_queue():
    """Return an RQ Queue connected to Redis.

    Raises:
        ImportError: When rq package is not installed.
    """
    try:
        from rq import Queue  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "rq package is required for the queue worker. "
            "Install it with: pip install rq"
        ) from exc

    conn = _get_redis_connection()
    return Queue(settings.JOB_QUEUE_NAME, connection=conn)


# ---------------------------------------------------------------------------
# Enqueue API (called from API routes)
# ---------------------------------------------------------------------------


def enqueue_job(db_job_id: int) -> str:
    """Enqueue an existing AsyncJob record for background execution.

    The job record must already exist in the database (created via
    job_repository.create_job). This function hands the job_id to RQ so
    the worker process can call run_job(job_id).

    Args:
        db_job_id: Primary key of the AsyncJob record to process.

    Returns:
        RQ job ID string (UUID assigned by RQ, not the DB primary key).

    Raises:
        ImportError: If redis/rq packages are not installed.
        redis.exceptions.ConnectionError: If Redis is unreachable.
    """
    from app.workers.job_runner import run_job  # noqa: PLC0415

    queue = _get_queue()
    rq_job = queue.enqueue(
        run_job,
        db_job_id,
        retry=_build_retry(),
        job_timeout=600,  # 10-minute hard timeout per job
    )
    logger.info("Enqueued DB job %s as RQ job %s", db_job_id, rq_job.id)
    return rq_job.id


def enqueue_ingest_job(db_job_id: int) -> str:
    """Convenience wrapper: enqueue an ingest job.

    Equivalent to enqueue_job(db_job_id). Exposed as a named function so
    API routes can be tested by patching 'app.api.routes.enqueue_ingest_job'.
    """
    return enqueue_job(db_job_id)


def enqueue_generate_job(db_job_id: int) -> str:
    """Convenience wrapper: enqueue a generate job.

    Equivalent to enqueue_job(db_job_id). Exposed as a named function so
    API routes can be tested by patching 'app.api.routes.enqueue_generate_job'.
    """
    return enqueue_job(db_job_id)


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------


def _build_retry() -> Optional[object]:
    """Build an RQ Retry object from settings.

    Returns None when rq is not installed (graceful fallback for tests).
    """
    try:
        from rq.job import Retry  # noqa: PLC0415

        # Exponential-ish backoff: [5, 10, 20] seconds for 3 retries
        delays = [
            settings.JOB_RETRY_DELAY_SECONDS * (2**i)
            for i in range(settings.JOB_MAX_RETRIES)
        ]
        return Retry(max=settings.JOB_MAX_RETRIES, interval=delays)
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Worker entrypoint (blocking)
# ---------------------------------------------------------------------------


def start_worker() -> None:
    """Start a blocking RQ worker that processes the configured queue.

    This function runs forever (until interrupted). Run it in a separate
    process or container from the Flask API server.

    Raises:
        ImportError: If redis/rq packages are not installed.
        redis.exceptions.ConnectionError: If Redis is unreachable.
    """
    try:
        from rq import Worker  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "rq package is required for the queue worker. "
            "Install it with: pip install rq"
        ) from exc

    conn = _get_redis_connection()
    queue = _get_queue()

    logger.info(
        "Starting queue worker — queue=%s redis=%s",
        settings.JOB_QUEUE_NAME,
        settings.REDIS_URL,
    )
    worker = Worker([queue], connection=conn)
    worker.work(with_scheduler=False)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        start_worker()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
        sys.exit(0)
    except ImportError as exc:
        logger.error("Missing dependency: %s", exc)
        sys.exit(1)
