"""Paired local sub-pixel refinement for lunar correspondences.

Independent corner snapping can move a valid cross-sensor match to unrelated
corners. This module keeps the reference point fixed and searches for its
gradient pattern near the source point; a quadratic interpolation of the
correlation peak supplies the sub-pixel source coordinate.
"""

from __future__ import annotations

import cv2
import numpy as np


def _gradient_magnitude(image: np.ndarray) -> np.ndarray:
    """Return a float32, illumination-robust local-structure image."""
    image_f = image.astype(np.float32)
    gx = cv2.Sobel(image_f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(image_f, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def _quadratic_peak_offset(values: np.ndarray, index: int) -> float:
    """Estimate a one-dimensional peak offset in [-1, 1]."""
    if index <= 0 or index >= len(values) - 1:
        return 0.0
    left = float(values[index - 1])
    center = float(values[index])
    right = float(values[index + 1])
    denominator = left - 2.0 * center + right
    if abs(denominator) < 1e-8:
        return 0.0
    return float(np.clip(0.5 * (left - right) / denominator, -1.0, 1.0))


def refine_matches(
    source_image: np.ndarray,
    reference_image: np.ndarray,
    source_points: np.ndarray,
    reference_points: np.ndarray,
    template_radius: int = 7,
    search_radius: int = 5,
    min_correlation: float = 0.20,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Refine correspondences with paired gradient NCC.

    Inputs must already be approximately scale-aligned. Unreliable points are
    retained unchanged instead of being forced onto unrelated image corners.
    """
    if source_image.dtype != np.uint8 or reference_image.dtype != np.uint8:
        raise TypeError("Paired sub-pixel refinement requires uint8 grayscale images")
    if source_image.ndim != 2 or reference_image.ndim != 2:
        raise ValueError("Paired sub-pixel refinement requires 2D grayscale images")
    if len(source_points) != len(reference_points):
        raise ValueError("Source and reference point counts must match")
    if template_radius < 2 or search_radius < 1:
        raise ValueError("template_radius must be >= 2 and search_radius >= 1")

    src_points = source_points.astype(np.float32, copy=True)
    ref_points = reference_points.astype(np.float32, copy=True)
    refined_src = src_points.copy()
    scores = np.full(len(src_points), np.nan, dtype=np.float32)
    src_grad = _gradient_magnitude(source_image)
    ref_grad = _gradient_magnitude(reference_image)
    margin = template_radius + search_radius

    for index, (src_pt, ref_pt) in enumerate(zip(src_points, ref_points, strict=True)):
        sx, sy = int(round(float(src_pt[0]))), int(round(float(src_pt[1])))
        rx, ry = int(round(float(ref_pt[0]))), int(round(float(ref_pt[1])))
        if (
            sx - margin < 0
            or sx + margin >= source_image.shape[1]
            or sy - margin < 0
            or sy + margin >= source_image.shape[0]
            or rx - template_radius < 0
            or rx + template_radius >= reference_image.shape[1]
            or ry - template_radius < 0
            or ry + template_radius >= reference_image.shape[0]
        ):
            continue

        template = ref_grad[
            ry - template_radius : ry + template_radius + 1,
            rx - template_radius : rx + template_radius + 1,
        ]
        search = src_grad[
            sy - margin : sy + margin + 1,
            sx - margin : sx + margin + 1,
        ]
        response = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
        _, peak_score, _, peak = cv2.minMaxLoc(response)
        if not np.isfinite(peak_score) or peak_score < min_correlation:
            continue

        peak_x, peak_y = peak
        offset_x = _quadratic_peak_offset(response[peak_y, :], peak_x)
        offset_y = _quadratic_peak_offset(response[:, peak_x], peak_y)
        refined_src[index] = (
            sx - search_radius + peak_x + offset_x,
            sy - search_radius + peak_y + offset_y,
        )
        scores[index] = peak_score

    displacement = np.linalg.norm(refined_src - src_points, axis=1)
    accepted = np.isfinite(scores)
    stats = {
        "method": "paired_gradient_ncc_quadratic_peak",
        "total_points": int(len(src_points)),
        "successfully_refined": int(accepted.sum()),
        "unrefinable_points": int((~accepted).sum()),
        "mean_displacement": float(displacement[accepted].mean()) if accepted.any() else 0.0,
        "max_displacement": float(displacement[accepted].max()) if accepted.any() else 0.0,
        "mean_correlation": float(scores[accepted].mean()) if accepted.any() else None,
    }
    return refined_src, ref_points, stats
