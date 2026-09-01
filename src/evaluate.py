"""
evaluate.py — Evaluation metrics for LunarCV registration.

Computes RMSE, spatial distribution (Convex Hull, Grid Occupancy),
and performs Cross-Validation.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull
from sklearn.model_selection import KFold

from transform import transform_points, estimate_transform

def calculate_reprojection_errors(
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    M: np.ndarray
) -> dict[str, float]:
    """
    Calculate Forward, Backward, and Symmetric Reprojection RMSE.
    M must map Reference -> Source.
    """
    if len(pts_src) == 0 or M is None:
        return {"fwd_rmse": np.nan, "bwd_rmse": np.nan, "sym_rmse": np.nan}
        
    try:
        M_inv = np.linalg.inv(M)
    except np.linalg.LinAlgError:
        return {"fwd_rmse": np.nan, "bwd_rmse": np.nan, "sym_rmse": np.nan}
        
    # Forward error: Transform Ref -> Src, compare with Src
    pred_src = transform_points(pts_ref, M)
    fwd_errors = np.linalg.norm(pts_src - pred_src, axis=1)
    
    # Backward error: Transform Src -> Ref, compare with Ref
    pred_ref = transform_points(pts_src, M_inv)
    bwd_errors = np.linalg.norm(pts_ref - pred_ref, axis=1)
    
    # Symmetric error
    sym_errors = (fwd_errors**2 + bwd_errors**2)
    
    return {
        "fwd_rmse": float(np.sqrt(np.mean(fwd_errors**2))),
        "bwd_rmse": float(np.sqrt(np.mean(bwd_errors**2))),
        "sym_rmse": float(np.sqrt(np.mean(sym_errors))),
        "fwd_median": float(np.median(fwd_errors)),
        "fwd_max": float(np.max(fwd_errors))
    }


def calculate_spatial_metrics(
    pts_src: np.ndarray,
    image_shape: tuple[int, int],
    grid_size: tuple[int, int] = (4, 4)
) -> dict[str, float]:
    """
    Calculate Convex Hull Coverage (%) and Grid Occupancy (%).
    """
    if len(pts_src) < 3:
        return {"hull_coverage": 0.0, "grid_occupancy": 0.0, "occupied_cells": 0}
        
    h, w = image_shape
    total_area = h * w
    
    # Convex Hull Coverage
    try:
        hull = ConvexHull(pts_src)
        hull_area = hull.volume
        hull_coverage = (hull_area / total_area) * 100.0
    except Exception:
        hull_coverage = 0.0
        
    # Grid Occupancy
    grid_rows, grid_cols = grid_size
    cell_h, cell_w = h / grid_rows, w / grid_cols
    
    occupied = set()
    for x, y in pts_src:
        r = min(int(max(0, y) / cell_h), grid_rows - 1)
        c = min(int(max(0, x) / cell_w), grid_cols - 1)
        occupied.add((r, c))
        
    total_cells = grid_rows * grid_cols
    grid_occupancy = (len(occupied) / total_cells) * 100.0
    
    return {
        "hull_coverage": hull_coverage,
        "grid_occupancy": grid_occupancy,
        "occupied_cells": len(occupied)
    }


def cross_validate_transform(
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    model: str = "homography",
    threshold: float = 4.0,
    n_splits: int = 5
) -> dict[str, float]:
    """
    Perform K-Fold Cross Validation on the points.
    Returns CV Reprojection RMSE.
    """
    if len(pts_src) < max(5, n_splits):
        return {"cv_rmse": np.nan, "cv_median": np.nan}
        
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    cv_errors = []
    
    for train_idx, test_idx in kf.split(pts_src):
        train_src, test_src = pts_src[train_idx], pts_src[test_idx]
        train_ref, test_ref = pts_ref[train_idx], pts_ref[test_idx]
        
        M, _ = estimate_transform(train_src, train_ref, model=model, ransac_reproj_threshold=threshold)
        
        if M is not None:
            pred_src = transform_points(test_ref, M)
            errs = np.linalg.norm(test_src - pred_src, axis=1)
            cv_errors.extend(errs)
            
    if not cv_errors:
        return {"cv_rmse": np.nan, "cv_median": np.nan}
        
    return {
        "cv_rmse": float(np.sqrt(np.mean(np.array(cv_errors)**2))),
        "cv_median": float(np.median(cv_errors))
    }
