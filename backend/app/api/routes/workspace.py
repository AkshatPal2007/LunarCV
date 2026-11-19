"""Real dataset availability, durable history and native-pixel visualization."""

import csv
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.api.routes.registration import _find_image, _job
from app.config import settings
from app.jobs import JobRepository
from app.schemas.workspace import (
    JobSummary,
    PairAvailability,
    ProductMetadata,
    VisualizationResponse,
)
from lunarcv.io.products import describe_product

router = APIRouter()


@router.get("/pairs", response_model=list[PairAvailability])
def available_pairs():
    manifest = settings.BASE_DIR / "data/metadata/demo_pair.json"
    if not manifest.is_file():
        return []
    pair = json.loads(manifest.read_text())
    source = settings.BASE_DIR / pair["source"]
    reference = settings.BASE_DIR / pair["reference"]
    available = (
        source.is_file()
        and reference.is_file()
        and source.with_suffix(".xml").is_file()
    )
    return [
        {
            "pair_id": pair["pair_id"],
            "name": "OHRC / LRO NAC · Development scene",
            "dataset_split": pair["dataset_split"],
            "source_product_id": source.stem,
            "reference_product_id": reference.stem,
            "source_sensor": pair["source_sensor"],
            "reference_sensor": pair["reference_sensor"],
            "available": available,
            "unavailable_reason": None
            if available
            else "Acquire the real mission images and OHRC XML label using the documented provider links",
            "prior_description": pair["prior_description"],
            "ground_truth_status": pair["ground_truth_status"],
            "registration_request": {
                "source_image_id": source.stem,
                "reference_image_id": reference.stem,
                "source_bounds": pair["source_bounds"],
                "reference_bounds": pair["reference_bounds"],
                "source_scale_xy": pair["source_scale_xy"],
            },
        }
    ]


@router.get("/images/{image_id}/metadata", response_model=ProductMetadata)
def image_metadata(image_id: str):
    import re

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", image_id):
        raise HTTPException(status_code=422, detail="Invalid image ID")
    path = _find_image(image_id)
    try:
        return {"file_id": image_id, "filename": path.name, **describe_product(path)}
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/jobs", response_model=list[JobSummary])
def job_history(limit: int = Query(30, ge=1, le=100)):
    return [
        {
            "job_id": job["job_id"],
            "status": job["status"],
            "progress": job.get("progress"),
            "message": job.get("message"),
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
            "quality_decision": (job.get("metrics") or {}).get("quality_decision"),
            "source_name": Path(job.get("source_path", "")).name,
            "reference_name": Path(job.get("reference_path", "")).name,
        }
        for job in JobRepository().list_recent(limit)
    ]


@router.get("/jobs/{job_id}/visualization", response_model=VisualizationResponse)
def visualization(job_id: str):
    job = _job(job_id)
    if job["status"] not in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=409, detail="Artifacts are not ready")
    directory = settings.RESULTS_DIR / job_id
    mapping_path = directory / "transform.json"
    mapping = json.loads(mapping_path.read_text()) if mapping_path.is_file() else None
    rows = []
    csv_path = directory / "correspondence_points.csv"
    if csv_path.is_file():
        with csv_path.open() as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    {
                        "point_id": int(row["point_id"]),
                        "source": [float(row["source_x"]), float(row["source_y"])],
                        "reference": [
                            float(row["reference_x"]),
                            float(row["reference_y"]),
                        ],
                        "confidence": float(row["primary_confidence"]),
                        "secondary_agreement": row["secondary_agreement"] == "True",
                        "refined": row["refined"] == "True",
                        "fit_residual_reference_px": float(
                            row["fit_residual_reference_px"]
                        ),
                    }
                )
    allowed = (
        "source.png",
        "reference.png",
        "registered.png",
        "overlay.png",
        "checkerboard.png",
        "matches.png",
        "valid_mask.png",
        "support_mask.png",
        "registered.tif",
        "transform.json",
        "metrics.json",
        "manifest.json",
        "correspondence_points.csv",
        "candidates.npz",
    )
    return {
        "job_id": job_id,
        "mapping": mapping,
        "points": rows,
        "artifacts": {
            name: f"{settings.API_V1_STR}/files/{job_id}/{name}"
            for name in allowed
            if (directory / name).is_file()
        },
    }
