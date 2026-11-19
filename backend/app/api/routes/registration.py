"""
Registration endpoints.
"""

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.jobs import JobRepository, now, submit_job
from app.schemas.common import JobStatus
from app.schemas.registration import (
    RegistrationJobCreate,
    RegistrationJobResponse,
    RegistrationJobStatus,
    RegistrationResults,
)
from app.services.validation_service import validate_registration_pair

logger = logging.getLogger(__name__)

router = APIRouter()


# Resolve a unique immutable product ID within configured storage roots.
def _find_image(image_id):
    files = []
    for root in (settings.RAW_DIR, settings.UPLOAD_DIR):
        files.extend(
            p
            for p in root.rglob(f"{image_id}.*")
            if p.is_file()
            and p.suffix.lower() in settings.ALLOWED_EXTENSIONS
            and p.resolve().is_relative_to(root.resolve())
        )
    if len(files) != 1:
        raise HTTPException(
            status_code=404 if not files else 409,
            detail="Image ID missing or ambiguous",
        )
    return files[0]


def _job(job_id):
    try:
        return JobRepository().get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


def _load_demo_job_results(job_id: str) -> RegistrationResults:
    """Load pre-existing demo results from static files."""
    if job_id == "showcase_submission":
        metrics_path = settings.BASE_DIR / "outputs" / "submission" / "metrics.json"
    elif job_id == "showcase_baseline":
        metrics_path = settings.RESULTS_DIR / "showcase_baseline_run" / "metrics.json"
    else:
        raise HTTPException(status_code=404, detail="Demo job not found")

    if not metrics_path.exists():
        logger.error("Demo job metrics not found at %s", metrics_path)
        raise HTTPException(status_code=404, detail="Demo job metrics not found")

    with open(metrics_path) as f:
        metrics = json.load(f)

    metrics["historical_run"] = True
    metrics["subpixel_accuracy_claim"] = False
    for diagnostic in (metrics, metrics.get("evaluation_metrics", {})):
        if "quality_decision" in diagnostic:
            diagnostic["historical_quality_decision"] = diagnostic["quality_decision"]
            diagnostic["quality_decision"] = "HISTORICAL_UNVALIDATED"
    return RegistrationResults(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        metrics=metrics,
        registered_image_url=f"/api/v1/files/{job_id}/registered.png",
        overlay_image_url=f"/api/v1/files/{job_id}/overlay.png",
        checkerboard_image_url=f"/api/v1/files/{job_id}/checkerboard.png",
        correspondence_csv_url=f"/api/v1/files/{job_id}/correspondence_points.csv",
        error=None,
    )


@router.post("/register", response_model=RegistrationJobResponse)
async def create_registration_job(request: RegistrationJobCreate):
    source = _find_image(request.source_image_id)
    reference = _find_image(request.reference_image_id)
    validation = validate_registration_pair(source, reference)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    from lunarcv.io.products import describe_product, validate_window
    from lunarcv.settings import RegistrationConfig

    try:
        for path, bounds in (
            (source, request.source_bounds),
            (reference, request.reference_bounds),
        ):
            validate_window(
                bounds, describe_product(path)["shape"], RegistrationConfig().max_pixels
            )
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "pending",
        "created_at": now(),
        "request": request.model_dump(),
        "source_path": str(source),
        "reference_path": str(reference),
    }
    try:
        JobRepository().create(job, settings.MAX_PENDING_JOBS)
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    try:
        submit_job(job_id, source, reference, request.model_dump())
    except Exception as exc:
        JobRepository().update(
            job_id, status="failed", error=str(exc), completed_at=now()
        )
        raise HTTPException(
            status_code=503, detail="Compute worker unavailable"
        ) from exc
    return RegistrationJobResponse(
        job_id=job_id, status=JobStatus.PENDING, created_at=job["created_at"]
    )


@router.get("/jobs/{job_id}", response_model=RegistrationJobStatus)
async def get_job_status(job_id: str):
    """Get the status of a registration job."""
    # Handle demo jobs
    if job_id in ["showcase_submission", "showcase_baseline"]:
        return RegistrationJobStatus(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            message="Historical artifacts; original execution timestamps unavailable",
            created_at=None,
            completed_at=None,
        )

    job = _job(job_id)
    return RegistrationJobStatus(
        job_id=job["job_id"],
        status=job["status"],
        progress=job.get("progress"),
        message=job.get("message"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
    )


@router.get("/jobs/{job_id}/results", response_model=RegistrationResults)
async def get_job_results(job_id: str):
    """Get the results of a completed registration job."""
    # Handle demo jobs
    if job_id in ["showcase_submission", "showcase_baseline"]:
        return _load_demo_job_results(job_id)

    job = _job(job_id)

    if job["status"] not in [
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    ]:
        raise HTTPException(
            status_code=400, detail=f"Job not ready. Current status: {job['status']}"
        )

    if (
        not job.get("metrics")
        and (settings.RESULTS_DIR / job_id / "metrics.json").is_file()
    ):
        job["metrics"] = json.loads(
            (settings.RESULTS_DIR / job_id / "metrics.json").read_text()
        )
    return RegistrationResults(
        job_id=job_id,
        status=job["status"],
        metrics=job.get("metrics"),
        registered_image_url=f"/api/v1/files/{job_id}/registered.png"
        if job["status"] == JobStatus.COMPLETED
        else None,
        overlay_image_url=f"/api/v1/files/{job_id}/overlay.png"
        if job["status"] == JobStatus.COMPLETED
        else None,
        checkerboard_image_url=f"/api/v1/files/{job_id}/checkerboard.png"
        if job["status"] == JobStatus.COMPLETED
        else None,
        correspondence_csv_url=f"/api/v1/files/{job_id}/correspondence_points.csv"
        if job["status"] == JobStatus.COMPLETED
        else None,
        transform_url=f"/api/v1/files/{job_id}/transform.json"
        if job["status"] == JobStatus.COMPLETED
        else None,
        science_raster_url=f"/api/v1/files/{job_id}/registered.tif"
        if job["status"] == JobStatus.COMPLETED
        else None,
        metrics_url=f"/api/v1/files/{job_id}/metrics.json"
        if (settings.RESULTS_DIR / job_id / "metrics.json").exists()
        else None,
        manifest_url=f"/api/v1/files/{job_id}/manifest.json"
        if job["status"] == JobStatus.COMPLETED
        else None,
        error=job.get("error"),
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    job = _job(job_id)
    if job["status"] not in ("pending", "processing"):
        raise HTTPException(status_code=409, detail="Job is already terminal")
    JobRepository().update(
        job_id,
        cancel_requested=True,
        message="Cancellation requested; checked at stage boundaries",
    )
    return {"job_id": job_id, "cancel_requested": True}
