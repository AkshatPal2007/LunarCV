"""
metrics.py — Evaluation and Quality Gate for LunarCV.
Centralises RMSE, spatial uniformity, inlier ratios and the
final quality gate decision (ACCEPT / REJECT).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Tuple

import numpy as np


@dataclass
class RegistrationMetrics:
    candidate_matches: int
    inlier_matches: int
    inlier_ratio: float
    rmse_forward: float
    rmse_backward: float
    spatial_uniformity: float
    overlap_pct: float
    execution_time_s: float
    decision: str


def calculate_rmse(
    pts_ref: np.ndarray,
    pts_src: np.ndarray,
    H: np.ndarray,
) -> Tuple[float, float]:
    """
    Forward and backward RMSE given homography H (ref → src).

    Forward:  H  @ pts_ref  →  compare with pts_src
    Backward: H⁻¹ @ pts_src  →  compare with pts_ref
    """
    if len(pts_ref) == 0 or len(pts_src) == 0 or H is None:
        return float("inf"), float("inf")

    def _transform(pts: np.ndarray, M: np.ndarray) -> np.ndarray:
        hom = np.hstack([pts, np.ones((len(pts), 1), dtype=np.float64)])
        warped = (M @ hom.T).T
        return warped[:, :2] / warped[:, 2:3]

    fwd = np.linalg.norm(_transform(pts_ref, H) - pts_src, axis=1)
    rmse_fwd = float(np.sqrt(np.mean(fwd ** 2)))

    try:
        bwd = np.linalg.norm(_transform(pts_src, np.linalg.inv(H)) - pts_ref, axis=1)
        rmse_bwd = float(np.sqrt(np.mean(bwd ** 2)))
    except np.linalg.LinAlgError:
        rmse_bwd = float("inf")

    return rmse_fwd, rmse_bwd


def evaluate_spatial_uniformity(
    pts: np.ndarray,
    img_shape: Tuple[int, int],
    grid_size: Tuple[int, int] = (4, 4),
) -> float:
    """
    Coefficient of variation of match counts across a regular grid.
    Lower = more uniform. 0.0 = perfectly uniform.
    """
    if len(pts) == 0:
        return float("inf")

    h, w = img_shape
    grid_h, grid_w = h / grid_size[0], w / grid_size[1]

    counts = np.zeros(grid_size)
    for pt in pts:
        x, y = pt
        j = min(int(x / grid_w), grid_size[1] - 1)
        i = min(int(y / grid_h), grid_size[0] - 1)
        counts[i, j] += 1

    mean = np.mean(counts)
    if mean == 0:
        return float("inf")
    return float(np.std(counts) / mean)


def quality_gate(
    metrics: RegistrationMetrics,
    min_inliers: int = 6,        # Cross-sensor orbital strips yield 6-9 consistent inliers
    max_rmse: float = 2.0,       # Sub-pixel is excellent; 2px is still good for cross-sensor
    max_uniformity: float = 3.0, # Inherently clustered features in sparse cross-sensor pairs
) -> str:
    """
    Return "ACCEPT" or a "REJECT (<reason>)" string based on registration quality.
    Thresholds are calibrated for the OHRC ↔ LRO NAC cross-sensor scenario.
    """
    if metrics.inlier_matches < min_inliers:
        return "REJECT (Too few inliers)"
    if metrics.rmse_forward > max_rmse:
        return "REJECT (RMSE too high)"
    if metrics.spatial_uniformity > max_uniformity:
        return "REJECT (Poor spatial uniformity)"
    if metrics.overlap_pct < 5.0:
        return "REJECT (Overlap too small)"
    return "ACCEPT"
