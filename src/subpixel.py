"""
subpixel.py — Sub-pixel refinement of geometric correspondences.
"""
from __future__ import annotations

import cv2
import numpy as np


def refine_matches(
    source_image: np.ndarray,
    reference_image: np.ndarray,
    source_points: np.ndarray,
    reference_points: np.ndarray,
    win_size: tuple[int, int] = (5, 5),
    zero_zone: tuple[int, int] = (-1, -1),
    criteria: tuple[int, int, float] = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001),
    min_eigen_threshold: float = 1e-4,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Refines source and reference match points independently using cv2.cornerSubPix.

    Checks if points have sufficient local structure (minimum eigenvalue) and are within bounds.
    If a point is unsuitable, it retains its original coordinate and is marked as unrefinable.

    Returns:
        pts_src_refined : ndarray (N, 2)
        pts_ref_refined : ndarray (N, 2)
        stats : dict containing metrics
    """
    assert source_image.dtype == np.uint8 and source_image.ndim == 2
    assert reference_image.dtype == np.uint8 and reference_image.ndim == 2

    pts_src = source_points.copy().astype(np.float32)
    pts_ref = reference_points.copy().astype(np.float32)

    n_pts = len(pts_src)
    
    src_refined = pts_src.copy()
    ref_refined = pts_ref.copy()
    
    src_mask = np.zeros(n_pts, dtype=bool)
    ref_mask = np.zeros(n_pts, dtype=bool)

    def check_local_structure(img, pt, w_size):
        x, y = int(round(pt[0])), int(round(pt[1]))
        wx, wy = w_size
        if x - wx < 0 or x + wx >= img.shape[1] or y - wy < 0 or y + wy >= img.shape[0]:
            return False
        
        patch = img[y - wy : y + wy + 1, x - wx : x + wx + 1]
        eigen_img = cv2.cornerMinEigenVal(patch, blockSize=3, ksize=3)
        center_eigen = eigen_img[wy, wx]
        
        return center_eigen > min_eigen_threshold

    for i in range(n_pts):
        if check_local_structure(source_image, pts_src[i], win_size):
            p = np.array([[pts_src[i]]], dtype=np.float32)
            cv2.cornerSubPix(source_image, p, win_size, zero_zone, criteria)
            src_refined[i] = p[0, 0]
            src_mask[i] = True
            
        if check_local_structure(reference_image, pts_ref[i], win_size):
            p = np.array([[pts_ref[i]]], dtype=np.float32)
            cv2.cornerSubPix(reference_image, p, win_size, zero_zone, criteria)
            ref_refined[i] = p[0, 0]
            ref_mask[i] = True

    src_disp = np.linalg.norm(src_refined - pts_src, axis=1)
    ref_disp = np.linalg.norm(ref_refined - pts_ref, axis=1)
    
    tot_disp = src_disp + ref_disp
    both_refined = src_mask & ref_mask

    stats = {
        "total_points": n_pts,
        "successfully_refined": int(both_refined.sum()),
        "unrefinable_points": int(n_pts - both_refined.sum()),
        "mean_displacement": float(np.mean(tot_disp[both_refined])) if both_refined.any() else 0.0,
        "max_displacement": float(np.max(tot_disp[both_refined])) if both_refined.any() else 0.0,
    }

    return src_refined, ref_refined, stats
