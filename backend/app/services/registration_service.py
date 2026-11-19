"""API adapter for the same engine used by scripts/register_pair.py."""

import logging
import time
from pathlib import Path

from app.config import settings
from app.jobs import JobRepository, now

logger = logging.getLogger(__name__)


def run_registration(job_id, source_path, reference_path, request, db_path):
    from lunarcv.engine import RegistrationConfig, RegistrationEngine

    repository = JobRepository(db_path)
    started = time.monotonic()

    def progress(percent, message):
        job = repository.get(job_id)
        if job.get("cancel_requested"):
            raise InterruptedError("Cancelled by client")
        if time.monotonic() - started > settings.JOB_TIMEOUT_SECONDS:
            raise TimeoutError(
                "Registration exceeded configured stage-boundary time budget"
            )
        repository.update(job_id, progress=percent, message=message)

    try:
        progress(0, "Starting bounded compute worker")
        repository.update(job_id, status="processing", started_at=now())
        config = RegistrationConfig(
            matcher=request.get("matcher", "ensemble"),
            model=request.get("model", "affine"),
            features=request.get("features", "aliked"),
        )
        result = RegistrationEngine(config).run(
            Path(source_path),
            Path(reference_path),
            settings.RESULTS_DIR / job_id,
            source_bounds=request.get("source_bounds"),
            reference_bounds=request.get("reference_bounds"),
            source_scale_xy=request.get("source_scale_xy", (1.0, 1.0)),
            cache_dir=settings.CACHE_DIR,
            progress=progress,
            prior_description="API product windows; no independent geographic validation",
        )
        repository.update(
            job_id,
            status="completed",
            completed_at=now(),
            progress=100,
            metrics=result.metrics,
            message=f"Completed: {result.metrics['quality_decision']}",
        )
    except Exception as exc:
        status = "cancelled" if isinstance(exc, InterruptedError) else "failed"
        repository.update(
            job_id, status=status, completed_at=now(), error=str(exc), message=str(exc)
        )
        logger.exception("Registration %s %s", job_id, status)
