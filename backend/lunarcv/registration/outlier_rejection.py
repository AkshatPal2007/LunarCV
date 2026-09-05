"""
outlier_rejection.py — Geometric outlier rejection for LunarCV.

Wraps OpenCV MAGSAC++ to robustly filter false feature correspondences.

Usage:
    from outlier_rejection import magsac_filter
    mkpts_src_clean, mkpts_ref_clean, conf_clean, H, mask = magsac_filter(mkpts_src, mkpts_ref, conf)
"""

from __future__ import annotations

import cv2
import numpy as np


def magsac_filter(
    mkpts_src: np.ndarray,
    mkpts_ref: np.ndarray,
    conf: np.ndarray | None = None,
    model: str = "homography",
    ransac_reproj_threshold: float = 3.0,
    max_iters: int = 10000,
    confidence: float = 0.999,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None, np.ndarray]:
    """
    Apply OpenCV MAGSAC++ geometric outlier rejection.

    Parameters
    ----------
    mkpts_src : ndarray (N, 2)
        Source image match keypoints (x, y).
    mkpts_ref : ndarray (N, 2)
        Reference image match keypoints (x, y).
    conf : ndarray (N,) or None
        Per-match confidence scores from LoFTR.
    model : str
        Geometric model to fit: 'homography' (default) or 'fundamental'.
    ransac_reproj_threshold : float
        MAGSAC++ reprojection error threshold in pixels (default 3.0).
    max_iters : int
        Maximum RANSAC iterations (default 10000).
    confidence : float
        Desired solution confidence in [0, 1] (default 0.999).

    Returns
    -------
    mkpts_src_clean : ndarray (M, 2)    — inlier source keypoints
    mkpts_ref_clean : ndarray (M, 2)    — inlier reference keypoints
    conf_clean      : ndarray (M,) | None
    H               : ndarray (3, 3) | None — fitted homography (None if fundamental)
    mask            : ndarray (N,) bool — full inlier mask over input
    """
    if len(mkpts_src) < 4:
        print(f"[MAGSAC++] Only {len(mkpts_src)} matches — need ≥4. Returning empty.")
        empty = np.empty((0, 2), dtype=np.float32)
        return empty, empty, None, None, np.zeros(len(mkpts_src), dtype=bool)

    pts_src = mkpts_src.astype(np.float32)
    pts_ref = mkpts_ref.astype(np.float32)

    if model == "homography":
        # Estimate H mapping pts_ref (LRO reference) -> pts_src (TMC-2 target)
        M, raw_mask = cv2.findHomography(
            pts_ref,
            pts_src,
            method=cv2.USAC_MAGSAC,
            ransacReprojThreshold=ransac_reproj_threshold,
            maxIters=max_iters,
            confidence=confidence,
        )
    else:  # fundamental
        M, raw_mask = cv2.findFundamentalMat(
            pts_src,
            pts_ref,
            method=cv2.USAC_MAGSAC,
            ransacReprojThreshold=ransac_reproj_threshold,
            maxIters=max_iters,
            confidence=confidence,
        )

    if raw_mask is None:
        print("[MAGSAC++] No valid model found — returning empty.")
        empty = np.empty((0, 2), dtype=np.float32)
        return empty, empty, None, None, np.zeros(len(mkpts_src), dtype=bool)

    mask = raw_mask.ravel().astype(bool)
    n_inliers = mask.sum()
    inlier_ratio = n_inliers / len(mask)

    print(
        f"[MAGSAC++] Total: {len(mask)}  Inliers: {n_inliers}  "
        f"Inlier ratio: {inlier_ratio:.3f}  Model: {model}"
    )

    mkpts_src_clean = pts_src[mask]
    mkpts_ref_clean = pts_ref[mask]
    conf_clean = conf[mask] if conf is not None else None
    H = M if model == "homography" else None

    return mkpts_src_clean, mkpts_ref_clean, conf_clean, H, mask


def print_match_stats(
    mkpts_src: np.ndarray,
    mkpts_ref: np.ndarray,
    conf: np.ndarray | None,
    label: str = "matches",
) -> None:
    """Print summary statistics for a set of match pairs."""
    print(f"--- {label} ---")
    print(f"  Count : {len(mkpts_src)}")
    if conf is not None:
        print(
            f"  Conf  : min={conf.min():.3f}  max={conf.max():.3f}  mean={conf.mean():.3f}"
        )
    if len(mkpts_src) > 0:
        # Residuals in source image
        print(
            f"  Src   : x=[{mkpts_src[:, 0].min():.1f}, {mkpts_src[:, 0].max():.1f}]  "
            f"y=[{mkpts_src[:, 1].min():.1f}, {mkpts_src[:, 1].max():.1f}]"
        )
        print(
            f"  Ref   : x=[{mkpts_ref[:, 0].min():.1f}, {mkpts_ref[:, 0].max():.1f}]  "
            f"y=[{mkpts_ref[:, 1].min():.1f}, {mkpts_ref[:, 1].max():.1f}]"
        )
