"""
Configuration endpoints for the frontend to fetch processing parameters.
"""

import csv
from pathlib import Path

from fastapi import APIRouter, HTTPException

from lunarcv import processing_config
from app.config import settings

router = APIRouter()


@router.get("/config/correspondence-points")
async def get_correspondence_points():
    """
    Get correspondence points from the showcase submission.
    Returns CSV data as JSON.
    """
    csv_path = settings.BASE_DIR / "outputs" / "submission" / "correspondence_points.csv"

    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Correspondence points file not found")

    points = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            points.append({
                'point_id': int(row['point_id']),
                'ohrc_patch_x': float(row['ohrc_patch_x']),
                'ohrc_patch_y': float(row['ohrc_patch_y']),
                'lro_crop_x': float(row['lro_crop_x']),
                'lro_crop_y': float(row['lro_crop_y']),
                'fit_residual_px': float(row['fit_residual_px'])
            })

    return {"points": points}


@router.get("/config/processing")
async def get_processing_config():
    """
    Get the actual processing parameters used in the registration pipeline.

    Returns real backend constants instead of placeholder values.
    """
    return {
        "normalization": {
            "percentile_low": processing_config.PERCENTILE_LOW,
            "percentile_high": processing_config.PERCENTILE_HIGH,
        },
        "clahe": {
            "enabled": processing_config.CLAHE_ENABLED,
            "clip_limit": processing_config.CLAHE_CLIP_LIMIT,
            "tile_grid_size": processing_config.CLAHE_TILE_GRID_SIZE,
        },
        "lightglue": {
            "max_dim": processing_config.LIGHTGLUE_MAX_DIM,
            "max_keypoints": processing_config.LIGHTGLUE_MAX_KEYPOINTS,
            "conf_threshold": processing_config.LIGHTGLUE_CONF_THRESHOLD,
        },
        "strip_matching": {
            "strip_height_min": processing_config.STRIP_HEIGHT_MIN,
            "strip_height_max": processing_config.STRIP_HEIGHT_MAX,
            "strip_height_divisor": processing_config.STRIP_HEIGHT_DIVISOR,
            "strip_overlap_min": processing_config.STRIP_OVERLAP_MIN,
            "strip_overlap_divisor": processing_config.STRIP_OVERLAP_DIVISOR,
        },
        "rift2": {
            "threshold": processing_config.RIFT2_THRESHOLD,
        },
        "magsac": {
            "reproj_threshold": processing_config.MAGSAC_REPROJ_THRESHOLD,
            "max_iters": processing_config.MAGSAC_MAX_ITERS,
            "confidence": processing_config.MAGSAC_CONFIDENCE,
            "model": processing_config.MAGSAC_MODEL,
        },
        "spatial_uniformity": {
            "grid_rows": processing_config.SPATIAL_GRID_ROWS,
            "grid_cols": processing_config.SPATIAL_GRID_COLS,
            "top_k_per_cell": processing_config.SPATIAL_TOP_K_PER_CELL,
        },
        "subpixel": {
            "enabled": processing_config.SUBPIXEL_ENABLED,
            "method": processing_config.SUBPIXEL_METHOD,
            "win_size": processing_config.SUBPIXEL_WIN_SIZE,
            "max_iter": processing_config.SUBPIXEL_MAX_ITER,
            "epsilon": processing_config.SUBPIXEL_EPSILON,
        },
        "transform": {
            "model": processing_config.TRANSFORM_MODEL,
        },
    }
