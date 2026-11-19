"""
Configuration endpoints for the frontend to fetch processing parameters.
"""

import csv

from fastapi import APIRouter, HTTPException

from app.config import settings
from lunarcv.models.objects import TransformModel

router = APIRouter()


@router.get("/config/correspondence-points", deprecated=True)
async def get_correspondence_points():
    """
    Get correspondence points from the showcase submission.
    Returns CSV data as JSON.
    """
    csv_path = (
        settings.BASE_DIR / "outputs" / "submission" / "correspondence_points.csv"
    )

    if not csv_path.exists():
        raise HTTPException(
            status_code=404, detail="Correspondence points file not found"
        )

    points = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            points.append(
                {
                    "point_id": int(row["point_id"]),
                    "ohrc_patch_x": float(row["ohrc_patch_x"]),
                    "ohrc_patch_y": float(row["ohrc_patch_y"]),
                    "lro_crop_x": float(row["lro_crop_x"]),
                    "lro_crop_y": float(row["lro_crop_y"]),
                    "fit_residual_px": float(row["fit_residual_px"]),
                }
            )

    return {
        "points": points,
        "historical_run": True,
        "coordinate_frame": "historical_processing_pixels_not_native",
        "independent_accuracy": "unavailable",
    }


@router.get("/config/transform-matrix", deprecated=True)
async def get_transform_matrix():
    """
    Get the transform matrix from the showcase submission pipeline.
    Returns the 3x3 transformation matrix as JSON.
    """
    meta_path = (
        settings.BASE_DIR
        / "outputs"
        / "pipeline"
        / "ohrc_to_lro_registration"
        / "transform"
        / "transform_meta.json"
    )

    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Transform matrix file not found")

    transform = TransformModel.load(meta_path)

    return {
        "historical_run": True,
        "coordinate_frame": "historical_processing_pixels_not_native",
        "independent_accuracy": "unavailable",
        "transform_type": transform.transform_type,
        "matrix": transform.matrix.tolist(),
        "mean_error": transform.mean_error,
        "rmse": transform.rmse,
    }


@router.get("/config/processing")
async def get_processing_config():
    """
    Get the actual processing parameters used in the registration pipeline.

    Returns real backend constants instead of placeholder values.
    """
    from lunarcv.settings import RegistrationConfig

    config = RegistrationConfig()
    return {
        "engine_config": config.model_dump(),
        "normalization": {"percentile_low": 1.0, "percentile_high": 99.0},
        "clahe": {"enabled": False, "clip_limit": None, "tile_grid_size": None},
        "lightglue": {
            "features": config.features,
            "max_dim": config.max_dim,
            "max_keypoints": config.max_keypoints,
            "conf_threshold": 0.0,
        },
        "strip_matching": {
            "enabled": False,
            "replacement": "geographic or coarse-geometric guided 2D tiles",
        },
        "rift2": {
            "policy": "parallel agreement; learned primary fallback",
            "max_dimension": 1024,
            "cpu_workers": 2,
        },
        "magsac": {
            "reproj_threshold": config.reprojection_threshold,
            "model": config.model,
            "max_iters": 10000,
            "confidence": 0.999,
        },
        "spatial_uniformity": {
            "grid_rows": config.grid_rows,
            "grid_cols": config.grid_cols,
            "top_k_per_cell": config.top_k,
        },
        "subpixel": {
            "enabled": config.refine,
            "method": "fractional_gradient_ncc_bidirectional",
        },
        "transform": {
            "model": config.model,
            "direction": "native source -> native reference",
        },
        "accuracy_claim": "unavailable until independently validated",
    }
