"""
metrics.py — Evaluation and Quality Gate for LunarCV.
Centralises RMSE, spatial uniformity, inlier ratios and the
final quality gate decision (ACCEPT / REJECT).
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
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
    heldout_rmse_forward: float | None = None
    heldout_rmse_backward: float | None = None
    evaluation_status: str = "fit_only_pending_independent_validation"


@dataclass(frozen=True)
class HoldoutEvaluation:
    """Result of fitting on one partition and scoring a disjoint partition."""

    fit_count: int
    heldout_count: int
    fit_indices: tuple[int, ...]
    heldout_indices: tuple[int, ...]
    rmse_forward: float | None
    rmse_backward: float | None
    status: str


def calculate_rmse(
    pts_ref: np.ndarray,
    pts_src: np.ndarray,
    H: np.ndarray,
) -> tuple[float, float]:
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
    rmse_fwd = float(np.sqrt(np.mean(fwd**2)))

    try:
        bwd = np.linalg.norm(_transform(pts_src, np.linalg.inv(H)) - pts_ref, axis=1)
        rmse_bwd = float(np.sqrt(np.mean(bwd**2)))
    except np.linalg.LinAlgError:
        rmse_bwd = float("inf")

    return rmse_fwd, rmse_bwd


def deterministic_holdout_split(
    count: int,
    holdout_fraction: float = 0.2,
    seed: int = 20260910,
    min_fit: int = 4,
    min_holdout: int = 2,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Return reproducible disjoint fit/holdout indices.

    The seed is part of the frozen evaluation protocol. Returning ``None``
    prevents tiny point sets from being presented as validated accuracy.
    """
    if count < min_fit + min_holdout:
        return None
    if not 0.0 < holdout_fraction < 1.0:
        raise ValueError("holdout_fraction must be between 0 and 1")

    holdout_count = max(min_holdout, int(round(count * holdout_fraction)))
    holdout_count = min(holdout_count, count - min_fit)
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(count)
    heldout = np.sort(shuffled[:holdout_count])
    fit = np.sort(shuffled[holdout_count:])
    return fit, heldout


def evaluate_homography_holdout(
    pts_ref: np.ndarray,
    pts_src: np.ndarray,
    holdout_fraction: float = 0.2,
    seed: int = 20260910,
    min_fit: int = 4,
    min_holdout: int = 2,
) -> HoldoutEvaluation:
    """Fit robustly on fit points and score only disjoint raw candidates."""
    if len(pts_ref) != len(pts_src):
        raise ValueError("Reference and source point counts must match")

    split = deterministic_holdout_split(
        len(pts_ref), holdout_fraction, seed, min_fit, min_holdout
    )
    if split is None:
        return HoldoutEvaluation(
            fit_count=0,
            heldout_count=0,
            fit_indices=(),
            heldout_indices=(),
            rmse_forward=None,
            rmse_backward=None,
            status="insufficient_points_for_holdout",
        )

    fit_indices, heldout_indices = split
    M, _ = cv2.estimateAffine2D(
        pts_ref[fit_indices].astype(np.float32),
        pts_src[fit_indices].astype(np.float32),
        method=cv2.RANSAC,
        ransacReprojThreshold=4.0,
        maxIters=10000,
        confidence=0.999,
    )
    H = np.vstack([M, [0.0, 0.0, 1.0]]) if M is not None else None
    if H is None or not np.all(np.isfinite(H)):
        return HoldoutEvaluation(
            fit_count=len(fit_indices),
            heldout_count=len(heldout_indices),
            fit_indices=tuple(int(i) for i in fit_indices),
            heldout_indices=tuple(int(i) for i in heldout_indices),
            rmse_forward=None,
            rmse_backward=None,
            status="holdout_fit_failed",
        )

    rmse_forward, rmse_backward = calculate_rmse(
        pts_ref[heldout_indices], pts_src[heldout_indices], H
    )
    return HoldoutEvaluation(
        fit_count=len(fit_indices),
        heldout_count=len(heldout_indices),
        fit_indices=tuple(int(i) for i in fit_indices),
        heldout_indices=tuple(int(i) for i in heldout_indices),
        rmse_forward=rmse_forward,
        rmse_backward=rmse_backward,
        status="heldout_valid",
    )


def evaluate_spatial_uniformity(
    pts: np.ndarray,
    img_shape: tuple[int, int],
    grid_size: tuple[int, int] = (4, 4),
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
    min_inliers: int = 6,  # Cross-sensor orbital strips yield 6-9 consistent inliers
    max_rmse: float = 2.0,  # Sub-pixel is excellent; 2px is still good for cross-sensor
    max_uniformity: float = 3.0,  # Inherently clustered features in sparse cross-sensor pairs
) -> str:
    """
    Return "ACCEPT" or a "REJECT (<reason>)" string based on registration quality.
    Thresholds are calibrated for the OHRC ↔ LRO NAC cross-sensor scenario.
    """
    if metrics.evaluation_status != "heldout_valid":
        return "REJECT (Held-out validation unavailable)"
    if metrics.inlier_matches < min_inliers:
        return "REJECT (Too few inliers)"
    if metrics.heldout_rmse_forward is None:
        return "REJECT (Held-out RMSE unavailable)"
    if metrics.heldout_rmse_forward > max_rmse:
        return "REJECT (RMSE too high)"
    if metrics.spatial_uniformity > max_uniformity:
        return "REJECT (Poor spatial uniformity)"
    if metrics.overlap_pct < 5.0:
        return "REJECT (Overlap too small)"
    return "ACCEPT"
