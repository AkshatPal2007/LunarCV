"""
transform.py — Transformation fitting and estimation for LunarCV.

Supports Similarity, Affine, and Homography transformations.
Isolates transformation geometry from outlier rejection and evaluation.
"""

from __future__ import annotations

import numpy as np
import cv2


def estimate_transform(
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    model: str = "homography",
    ransac_reproj_threshold: float = 4.0,
    max_iters: int = 10000,
    confidence: float = 0.999
) -> tuple[np.ndarray | None, np.ndarray]:
    """
    Estimate a geometric transform mapping from pts_ref (LRO) to pts_src (OHRC)
    using MAGSAC++ (if homography/fundamental) or standard RANSAC (if affine).
    
    IMPORTANT: 
    Since we map from Reference (LRO) to Source (OHRC) space, the arguments to
    cv2 functions are (pts_ref, pts_src).
    
    Parameters
    ----------
    pts_src : ndarray (N, 2)
        Source image keypoints (x, y).
    pts_ref : ndarray (N, 2)
        Reference image keypoints (x, y).
    model : str
        'similarity', 'affine', or 'homography' (default).
    ransac_reproj_threshold : float
        RANSAC/MAGSAC reprojection threshold.
        
    Returns
    -------
    M : ndarray (3, 3) | None
        Fitted 3x3 transformation matrix (None if fitting fails).
    mask : ndarray (N,) bool
        Boolean mask of inliers.
    """
    if len(pts_src) < 4:
        return None, np.zeros(len(pts_src), dtype=bool)

    src_f32 = pts_src.astype(np.float32)
    ref_f32 = pts_ref.astype(np.float32)
    
    if model == "homography":
        # H maps Reference -> Source
        M, raw_mask = cv2.findHomography(
            ref_f32,
            src_f32,
            method=cv2.USAC_MAGSAC,
            ransacReprojThreshold=ransac_reproj_threshold,
            maxIters=max_iters,
            confidence=confidence,
        )
    elif model == "affine":
        # cv2.estimateAffine2D maps Reference -> Source
        M_2x3, raw_mask = cv2.estimateAffine2D(
            ref_f32,
            src_f32,
            method=cv2.RANSAC,
            ransacReprojThreshold=ransac_reproj_threshold,
            maxIters=max_iters,
            confidence=confidence,
        )
        if M_2x3 is not None:
            M = np.vstack([M_2x3, [0, 0, 1]])
        else:
            M = None
    elif model == "similarity":
        # cv2.estimateAffinePartial2D (Similarity transform) maps Reference -> Source
        M_2x3, raw_mask = cv2.estimateAffinePartial2D(
            ref_f32,
            src_f32,
            method=cv2.RANSAC,
            ransacReprojThreshold=ransac_reproj_threshold,
            maxIters=max_iters,
            confidence=confidence,
        )
        if M_2x3 is not None:
            M = np.vstack([M_2x3, [0, 0, 1]])
        else:
            M = None
    else:
        raise ValueError(f"Unknown transform model: {model}")

    if raw_mask is None or M is None:
        return None, np.zeros(len(pts_src), dtype=bool)

    mask = raw_mask.ravel().astype(bool)
    return M, mask


def transform_points(pts: np.ndarray, M: np.ndarray) -> np.ndarray:
    """
    Apply a 3x3 transformation matrix to a set of 2D points.
    
    Parameters
    ----------
    pts : ndarray (N, 2)
        Input points.
    M : ndarray (3, 3)
        Transformation matrix.
        
    Returns
    -------
    pred_pts : ndarray (N, 2)
        Transformed points.
    """
    if len(pts) == 0:
        return np.empty((0, 2), dtype=np.float32)
        
    pts_3d = np.concatenate([pts, np.ones((len(pts), 1))], axis=1)
    pred_3d = (M @ pts_3d.T).T
    pred_2d = pred_3d[:, :2] / pred_3d[:, 2:]
    return pred_2d
