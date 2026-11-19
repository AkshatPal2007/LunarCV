"""Conservative paired gradient correlation; reference coordinates stay fixed.

Both neighborhoods are sampled at fractional centers. Callers must align local
scale/orientation first. Refinement precision is not independent accuracy.
"""

from __future__ import annotations

import cv2
import numpy as np


def _gradient_magnitude(image):
    image = image.astype(np.float32)
    return cv2.magnitude(
        cv2.Sobel(image, cv2.CV_32F, 1, 0), cv2.Sobel(image, cv2.CV_32F, 0, 1)
    )


def _quadratic_peak_offset(values, index):
    if index <= 0 or index >= len(values) - 1:
        return 0.0
    left, center, right = map(float, values[index - 1 : index + 2])
    denominator = left - 2 * center + right
    if denominator >= -1e-8:
        return 0.0
    return float(np.clip(0.5 * (left - right) / denominator, -0.5, 0.5))


def _inside(point, radius, shape):
    x, y = point
    return radius <= x < shape[1] - radius - 1 and radius <= y < shape[0] - radius - 1


def _locate(
    search_image,
    template_image,
    search_center,
    template_center,
    template_radius,
    search_radius,
    min_correlation,
):
    margin = template_radius + search_radius
    if not _inside(search_center, margin, search_image.shape) or not _inside(
        template_center, template_radius, template_image.shape
    ):
        return None
    template = cv2.getRectSubPix(
        template_image,
        (2 * template_radius + 1,) * 2,
        tuple(map(float, template_center)),
    )
    search = cv2.getRectSubPix(
        search_image, (2 * margin + 1,) * 2, tuple(map(float, search_center))
    )
    if np.std(template) < 1e-4:
        return None
    response = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, peak = cv2.minMaxLoc(response)
    x, y = peak
    if (
        not np.isfinite(score)
        or score < min_correlation
        or min(x, y) == 0
        or max(x, y) == 2 * search_radius
    ):
        return None
    # A perfect central match needs no parabolic correction (avoids identity bias).
    if x == search_radius and y == search_radius and score >= 1 - 1e-6:
        return np.asarray(search_center, dtype=np.float32), score
    competitors = response.copy()
    competitors[max(0, y - 1) : y + 2, max(0, x - 1) : x + 2] = -1
    if score - float(competitors.max()) < 0.03:
        return None
    dx = x - search_radius + _quadratic_peak_offset(response[y, :], x)
    dy = y - search_radius + _quadratic_peak_offset(response[:, x], y)
    if np.hypot(dx, dy) > 1.0:
        return None
    return np.asarray(search_center, dtype=np.float32) + [dx, dy], score


def refine_matches(
    source_image,
    reference_image,
    source_points,
    reference_points,
    template_radius=7,
    search_radius=3,
    min_correlation=0.7,
):
    for image in (source_image, reference_image):
        if image.dtype != np.uint8 or image.ndim != 2:
            raise ValueError("Refinement requires uint8 grayscale images")
    source_points = np.asarray(source_points, dtype=np.float32)
    reference_points = np.asarray(reference_points, dtype=np.float32)
    if (
        source_points.shape != reference_points.shape
        or source_points.ndim != 2
        or source_points.shape[1] != 2
    ):
        raise ValueError("Refinement requires paired Nx2 points")
    if not np.isfinite(source_points).all() or not np.isfinite(reference_points).all():
        raise ValueError("Non-finite refinement points")
    if template_radius < 2 or search_radius < 1:
        raise ValueError("Invalid correlation neighborhood")
    src, ref = _gradient_magnitude(source_image), _gradient_magnitude(reference_image)
    refined = source_points.copy()
    scores = np.full(len(refined), np.nan)
    for i, (sp, rp) in enumerate(zip(source_points, reference_points, strict=True)):
        found = _locate(
            src, ref, sp, rp, template_radius, search_radius, min_correlation
        )
        if found is None:
            continue
        candidate, score = found
        backward = _locate(
            ref, src, rp, candidate, template_radius, search_radius, min_correlation
        )
        if backward is None or np.linalg.norm(backward[0] - rp) > 0.35:
            continue
        refined[i], scores[i] = candidate, score
    accepted = np.isfinite(scores)
    displacement = np.linalg.norm(refined - source_points, axis=1)
    return (
        refined,
        reference_points.copy(),
        {
            "method": "fractional_gradient_ncc_bidirectional",
            "total_points": len(refined),
            "successfully_refined": int(accepted.sum()),
            "unrefinable_points": int((~accepted).sum()),
            "accepted_mask": accepted.tolist(),
            "mean_displacement": float(displacement[accepted].mean())
            if accepted.any()
            else 0.0,
            "max_displacement": float(displacement[accepted].max())
            if accepted.any()
            else 0.0,
            "mean_correlation": float(scores[accepted].mean())
            if accepted.any()
            else None,
        },
    )
