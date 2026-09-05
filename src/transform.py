"""
transform.py — Geometric transformation and image warping for LunarCV.

Handles:
  - Final homography estimation from correspondence points
  - Transformed corner computation to derive the valid bounding box
  - Translation-offset matrix construction (prevents cropping warped regions)
  - cv2.warpPerspective() for the reference and source images
  - Valid-pixel mask generation (LRO / OHRC / overlap)
  - Overlay (50/50 alpha blend) and checkerboard composites

Coordinate convention: all point arrays are (x, y) = (column, row), float32, Nx2.
H maps reference (LRO) coordinates → source (OHRC) coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Data class returned by compute_registration
# ---------------------------------------------------------------------------


@dataclass
class RegistrationResult:
    """All outputs of a single registration computation."""

    H: np.ndarray  # (3, 3) homography: ref → src
    H_warp: np.ndarray  # H pre-composed with translation T so no negative canvas coords
    T: np.ndarray  # (3, 3) pure translation matrix applied to OHRC
    warped_ref: np.ndarray  # warpPerspective(ref_img, H_warp)  — grayscale uint8
    warped_src: np.ndarray  # warpPerspective(src_img, T)        — grayscale uint8
    mask_ref: np.ndarray  # bool mask: valid pixels of warped_ref
    mask_src: np.ndarray  # bool mask: valid pixels of warped_src
    mask_overlap: np.ndarray  # bool mask: pixels valid in BOTH images
    canvas_shape: tuple[int, int]  # (height, width) of the output canvas
    warped_corners: np.ndarray  # (4, 2) reference image corners in source space
    bbox: tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    overlap_pct: float  # valid overlap / warped_ref area * 100


# ---------------------------------------------------------------------------
# Homography estimation
# ---------------------------------------------------------------------------


def estimate_homography(
    pts_ref: np.ndarray,
    pts_src: np.ndarray,
    method: int = 0,
) -> np.ndarray | None:
    """
    Estimate a homography H such that H @ pts_ref ≈ pts_src (ref → src).

    Parameters
    ----------
    pts_ref : ndarray (N, 2) — reference image (x, y) keypoints
    pts_src : ndarray (N, 2) — source image (x, y) keypoints
    method  : int — cv2.findHomography method flag (0 = least-squares, no RANSAC)
                    Use 0 here because MAGSAC++ has already cleaned the set.

    Returns
    -------
    H : ndarray (3, 3) or None
    """
    if len(pts_ref) < 4:
        return None
    H, _ = cv2.findHomography(
        pts_ref.astype(np.float32),
        pts_src.astype(np.float32),
        method=method,
    )
    return H


# ---------------------------------------------------------------------------
# Bounding-box computation
# ---------------------------------------------------------------------------


def compute_warped_bbox(
    H: np.ndarray,
    ref_h: int,
    ref_w: int,
    max_canvas: int = 20_000,
) -> tuple[np.ndarray, int, int, int, int]:
    """
    Transform the four corners of the reference image through H and compute
    the bounding box of the resulting quadrilateral.

    Parameters
    ----------
    H         : ndarray (3, 3) — homography mapping ref → src
    ref_h, ref_w : int — reference image dimensions
    max_canvas : int — safety cap on output canvas size (pixels)

    Returns
    -------
    warped_corners : ndarray (4, 2)  — transformed corners (x, y)
    x_min, y_min, x_max, y_max : int — bounding box in src space
    """
    corners = np.array(
        [[0, 0], [ref_w, 0], [ref_w, ref_h], [0, ref_h]],
        dtype=np.float32,
    ).reshape(-1, 1, 2)

    warped = cv2.perspectiveTransform(corners, H).reshape(-1, 2)

    x_min = int(np.floor(warped[:, 0].min()))
    y_min = int(np.floor(warped[:, 1].min()))
    x_max = int(np.ceil(warped[:, 0].max()))
    y_max = int(np.ceil(warped[:, 1].max()))

    out_w = x_max - x_min
    out_h = y_max - y_min

    if out_w > max_canvas or out_h > max_canvas:
        print(
            f"  [WARN] Warped canvas ({out_w}×{out_h}) exceeds {max_canvas}px safety cap. "
            "The homography may be physically unreliable (too few / poorly distributed inliers)."
        )
        x_max = x_min + min(out_w, max_canvas)
        y_max = y_min + min(out_h, max_canvas)

    return warped, x_min, y_min, x_max, y_max


# ---------------------------------------------------------------------------
# Translation matrix
# ---------------------------------------------------------------------------


def build_translation(tx: float, ty: float) -> np.ndarray:
    """
    Build a 3×3 homogeneous translation matrix that shifts by (tx, ty).

    Parameters
    ----------
    tx, ty : float — x and y pixel offsets

    Returns
    -------
    T : ndarray (3, 3) float64
    """
    return np.array(
        [[1, 0, tx], [0, 1, ty], [0, 0, 1]],
        dtype=np.float64,
    )


# ---------------------------------------------------------------------------
# Image warping and mask generation
# ---------------------------------------------------------------------------


def warp_images(
    ref_img: np.ndarray,
    src_img: np.ndarray,
    H: np.ndarray,
    canvas_w: int,
    canvas_h: int,
    x_min: int,
    y_min: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Warp both images onto a common canvas whose top-left corner is (x_min, y_min)
    in original source coordinates.

    Applies a translation T = [-x_min, -y_min] so that the warped region
    starts at (0, 0) on the canvas instead of at a possibly negative offset.

    H maps ref → src.  src is only translated (T), not warped.

    Parameters
    ----------
    ref_img  : ndarray (H_r, W_r) uint8 grayscale — reference image
    src_img  : ndarray (H_s, W_s) uint8 grayscale — source image
    H        : ndarray (3, 3) — homography ref → src
    canvas_w, canvas_h : int — output canvas size
    x_min, y_min : int — bounding-box offset (used to build T)

    Returns
    -------
    H_warp      : ndarray (3, 3) — H pre-composed with T
    T           : ndarray (3, 3) — translation matrix
    warped_ref  : ndarray (canvas_h, canvas_w) uint8
    warped_src  : ndarray (canvas_h, canvas_w) uint8
    mask_ref    : ndarray (canvas_h, canvas_w) bool
    mask_src    : ndarray (canvas_h, canvas_w) bool
    """
    T = build_translation(-x_min, -y_min)
    H_warp = T @ H

    warped_ref = cv2.warpPerspective(ref_img, H_warp, (canvas_w, canvas_h))
    warped_src = cv2.warpPerspective(src_img, T, (canvas_w, canvas_h))

    # Binary masks: True where the image contributes a valid (non-border) pixel
    mask_ref = (
        cv2.warpPerspective(
            np.ones_like(ref_img, dtype=np.uint8) * 255, H_warp, (canvas_w, canvas_h)
        )
        > 0
    )
    mask_src = (
        cv2.warpPerspective(
            np.ones_like(src_img, dtype=np.uint8) * 255, T, (canvas_w, canvas_h)
        )
        > 0
    )

    return H_warp, T, warped_ref, warped_src, mask_ref, mask_src


# ---------------------------------------------------------------------------
# Composite images (overlay + checkerboard)
# ---------------------------------------------------------------------------


def make_overlay(
    warped_ref: np.ndarray,
    warped_src: np.ndarray,
    mask_ref: np.ndarray,
    mask_src: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build a 50/50 alpha-blend overlay and the common valid-overlap mask.

    Outside the ref area, show src only; outside src area, show ref only;
    in the overlap region, blend 50/50.

    Parameters
    ----------
    warped_ref : ndarray (H, W) uint8 — warped reference
    warped_src : ndarray (H, W) uint8 — warped source
    mask_ref   : ndarray (H, W) bool
    mask_src   : ndarray (H, W) bool

    Returns
    -------
    overlay     : ndarray (H, W, 3) uint8 — BGR colour overlay
    mask_overlap: ndarray (H, W) bool — True where both images are valid
    """
    out_h, out_w = warped_ref.shape
    mask_overlap = mask_ref & mask_src

    lro_c = cv2.cvtColor(warped_ref, cv2.COLOR_GRAY2BGR)
    ohrc_c = cv2.cvtColor(warped_src, cv2.COLOR_GRAY2BGR)

    overlay = np.zeros((out_h, out_w, 3), dtype=np.uint8)
    overlay[mask_ref] = lro_c[mask_ref]
    overlay[mask_src] = ohrc_c[mask_src]
    overlay[mask_overlap] = (lro_c[mask_overlap] // 2) + (ohrc_c[mask_overlap] // 2)

    return overlay, mask_overlap


def make_checkerboard(
    warped_ref: np.ndarray,
    warped_src: np.ndarray,
    mask_ref: np.ndarray,
    mask_src: np.ndarray,
    mask_overlap: np.ndarray,
    grid_size: int = 50,
) -> np.ndarray:
    """
    Build a checkerboard comparison image alternating between warped_ref and
    warped_src in the overlap region. Outside the overlap, show the available image.

    Parameters
    ----------
    warped_ref, warped_src : ndarray (H, W) uint8
    mask_ref, mask_src, mask_overlap : ndarray (H, W) bool
    grid_size : int — side length of one checkerboard square in pixels

    Returns
    -------
    checker : ndarray (H, W) uint8
    """
    out_h, out_w = warped_ref.shape
    y, x = np.mgrid[0:out_h, 0:out_w]
    cell_mask = ((x // grid_size) + (y // grid_size)) % 2 == 0

    checker = np.zeros_like(warped_ref)
    checker[mask_ref] = warped_ref[mask_ref]
    checker[mask_src] = warped_src[mask_src]
    checker[mask_overlap & cell_mask] = warped_ref[mask_overlap & cell_mask]
    checker[mask_overlap & ~cell_mask] = warped_src[mask_overlap & ~cell_mask]

    return checker


# ---------------------------------------------------------------------------
# One-shot registration helper
# ---------------------------------------------------------------------------


def compute_registration(
    ref_img: np.ndarray,
    src_img: np.ndarray,
    pts_ref: np.ndarray,
    pts_src: np.ndarray,
    max_canvas: int = 20_000,
    checkerboard_grid_size: int = 50,
) -> RegistrationResult | None:
    """
    Full registration pipeline for a single image pair:
      1. Estimate H (ref → src) from refined inlier correspondences.
      2. Compute the warped bounding box of the reference image.
      3. Build translation T to place the warped region at canvas origin.
      4. Warp both images; compute masks.
      5. Build overlay and checkerboard composites.

    Parameters
    ----------
    ref_img  : ndarray uint8 grayscale — reference image (LRO NAC)
    src_img  : ndarray uint8 grayscale — source image (OHRC)
    pts_ref  : ndarray (N, 2) float32 — sub-pixel refined ref keypoints (x, y)
    pts_src  : ndarray (N, 2) float32 — sub-pixel refined src keypoints (x, y)
    max_canvas : int — safety cap on canvas size
    checkerboard_grid_size : int — checkerboard square side in pixels

    Returns
    -------
    RegistrationResult or None if homography estimation failed.
    """
    H = estimate_homography(pts_ref, pts_src)
    if H is None:
        return None

    ref_h, ref_w = ref_img.shape
    warped_corners, x_min, y_min, x_max, y_max = compute_warped_bbox(
        H, ref_h, ref_w, max_canvas
    )

    canvas_w = x_max - x_min
    canvas_h = y_max - y_min

    H_warp, T, warped_ref, warped_src, mask_ref, mask_src = warp_images(
        ref_img, src_img, H, canvas_w, canvas_h, x_min, y_min
    )

    overlay, mask_overlap = make_overlay(warped_ref, warped_src, mask_ref, mask_src)

    overlap_area = int(mask_overlap.sum())
    ref_area = int(mask_ref.sum())
    overlap_pct = 100.0 * overlap_area / max(1, ref_area)

    return RegistrationResult(
        H=H,
        H_warp=H_warp,
        T=T,
        warped_ref=warped_ref,
        warped_src=warped_src,
        mask_ref=mask_ref,
        mask_src=mask_src,
        mask_overlap=mask_overlap,
        canvas_shape=(canvas_h, canvas_w),
        warped_corners=warped_corners,
        bbox=(x_min, y_min, x_max, y_max),
        overlap_pct=overlap_pct,
    )
