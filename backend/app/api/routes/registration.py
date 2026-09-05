"""
Registration endpoints.
"""

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.config import settings
from app.schemas.registration import (
    RegistrationJobCreate,
    RegistrationJobResponse,
    RegistrationJobStatus,
    RegistrationResults,
)
from app.schemas.common import JobStatus
from app.services.registration_service import run_registration

router = APIRouter()

# In-memory job store (replace with Redis/database in production)
job_store = {}


@router.post("/register", response_model=RegistrationJobResponse)
async def create_registration_job(
    request: RegistrationJobCreate, background_tasks: BackgroundTasks
):
    """
    Start a registration job between source and reference images.

    Returns a job_id to poll for status and results.
    """
    # Validate that uploaded files exist
    source_files = list(settings.UPLOAD_DIR.glob(f"{request.source_image_id}.*"))
    reference_files = list(settings.UPLOAD_DIR.glob(f"{request.reference_image_id}.*"))

    if not source_files:
        raise HTTPException(status_code=404, detail="Source image not found")
    if not reference_files:
        raise HTTPException(status_code=404, detail="Reference image not found")

    # Create job
    job_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    job_store[job_id] = {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "created_at": created_at,
        "source_path": str(source_files[0]),
        "reference_path": str(reference_files[0]),
        "matcher": request.matcher,
    }

    # Start background processing
    background_tasks.add_task(
        run_registration,
        job_id=job_id,
        source_path=source_files[0],
        reference_path=reference_files[0],
        matcher=request.matcher,
        job_store=job_store,
    )

    return RegistrationJobResponse(
        job_id=job_id, status=JobStatus.PENDING, created_at=created_at
    )


@router.get("/jobs/{job_id}", response_model=RegistrationJobStatus)
async def get_job_status(job_id: str):
    """Get the status of a registration job."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_store[job_id]
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
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_store[job_id]

    if job["status"] not in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(
            status_code=400, detail=f"Job not ready. Current status: {job['status']}"
        )

    results_dir = settings.RESULTS_DIR / job_id

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
        error=job.get("error"),
    )
