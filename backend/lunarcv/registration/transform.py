"""
transform.py — Geometric transformation and image warping for LunarCV.

Handles:
  - Global transform estimation (Affine, Similarity, Homography)
  - Transformed corner computation to derive the valid bounding box
  - Single continuous global warping (cv2.warpAffine / cv2.warpPerspective)
  - Valid-pixel mask generation (LRO / OHRC / overlap)
  - Overlay (50/50 alpha blend) and checkerboard composites
  - Professional 4-panel visual verification suite

Coordinate convention: all point arrays are (x, y) = (column, row), float32, Nx2.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Data class returned by compute_registration
# ---------------------------------------------------------------------------


@dataclass
class RegistrationResult:
    """All outputs of a single registration computation."""

    H: np.ndarray  # (3, 3) transform: ref → src
    H_warp: np.ndarray  # H pre-composed with translation T so no negative canvas coords
    T: np.ndarray  # (3, 3) pure translation matrix applied to OHRC
    warped_ref: np.ndarray  # warped reference — grayscale uint8
    warped_src: np.ndarray  # warped source    — grayscale uint8
    mask_ref: np.ndarray  # bool mask: valid pixels of warped_ref
    mask_src: np.ndarray  # bool mask: valid pixels of warped_src
    mask_overlap: np.ndarray  # bool mask: pixels valid in BOTH images
    canvas_shape: tuple[int, int]  # (height, width) of the output canvas
    warped_corners: np.ndarray  # (4, 2) reference image corners in source space
    bbox: tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    overlap_pct: float  # valid overlap / warped_ref area * 100


# ---------------------------------------------------------------------------
# Transform estimation (Affine / Similarity / Homography)
# ---------------------------------------------------------------------------


def estimate_transform(
    pts_ref: np.ndarray,
    pts_src: np.ndarray,
    model: str = "affine",
    method: int = cv2.RANSAC,
) -> np.ndarray | None:
    """
    Estimate a 2D transform mapping ref → src coordinates.
    Returns a 3x3 homogeneous matrix.

    Parameters
    ----------
    pts_ref : ndarray (N, 2) — reference image (x, y) keypoints
    pts_src : ndarray (N, 2) — source image (x, y) keypoints
    model   : str — "affine" (6-DOF), "similarity" (4-DOF), or "homography" (8-DOF)
    method  : int — estimation flag (default: cv2.RANSAC)

    Returns
    -------
    H : ndarray (3, 3) or None
    """
    if len(pts_ref) < 3:
        return None

    pts_r = pts_ref.astype(np.float32)
    pts_s = pts_src.astype(np.float32)

    if model == "similarity":
        M, _ = cv2.estimateAffinePartial2D(pts_r, pts_s, method=method)
        if M is None:
            return None
        return np.vstack([M, [0.0, 0.0, 1.0]])

    elif model == "homography":
        if len(pts_ref) < 4:
            return None
        H, _ = cv2.findHomography(pts_r, pts_s, method=method)
        return H

    else:  # "affine" default
        M, _ = cv2.estimateAffine2D(pts_r, pts_s, method=method)
        if M is None:
            return None
        return np.vstack([M, [0.0, 0.0, 1.0]])


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
        x_max = x_min + min(out_w, max_canvas)
        y_max = y_min + min(out_h, max_canvas)

    return warped, x_min, y_min, x_max, y_max


# ---------------------------------------------------------------------------
# Translation matrix
# ---------------------------------------------------------------------------


def build_translation(tx: float, ty: float) -> np.ndarray:
    """Build a 3×3 homogeneous translation matrix."""
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
    Warp both images onto a common canvas whose top-left corner is (x_min, y_min).
    """
    T = build_translation(-x_min, -y_min)
    H_warp = T @ H

    warped_ref = cv2.warpPerspective(ref_img, H_warp, (canvas_w, canvas_h))
    warped_src = cv2.warpPerspective(src_img, T, (canvas_w, canvas_h))

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
# Composites: Overlay, Checkerboard, and Professional 4-Panel Suite
# ---------------------------------------------------------------------------


def make_overlay(
    warped_ref: np.ndarray,
    warped_src: np.ndarray,
    mask_ref: np.ndarray,
    mask_src: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a 50/50 alpha-blend overlay and the valid-overlap mask."""
    out_h, out_w = warped_ref.shape[:2]
    mask_overlap = mask_ref & mask_src

    ref_c = (
        cv2.cvtColor(warped_ref, cv2.COLOR_GRAY2BGR)
        if warped_ref.ndim == 2
        else warped_ref
    )
    src_c = (
        cv2.cvtColor(warped_src, cv2.COLOR_GRAY2BGR)
        if warped_src.ndim == 2
        else warped_src
    )

    overlay = np.zeros((out_h, out_w, 3), dtype=np.uint8)
    overlay[mask_ref] = ref_c[mask_ref]
    overlay[mask_src] = src_c[mask_src]
    overlay[mask_overlap] = (ref_c[mask_overlap] // 2) + (src_c[mask_overlap] // 2)

    return overlay, mask_overlap


def make_checkerboard(
    warped_ref: np.ndarray,
    warped_src: np.ndarray,
    mask_ref: np.ndarray,
    mask_src: np.ndarray,
    mask_overlap: np.ndarray,
    grid_size: int = 50,
) -> np.ndarray:
    """Build a checkerboard composite alternating in the overlap region."""
    out_h, out_w = warped_ref.shape[:2]
    y, x = np.mgrid[0:out_h, 0:out_w]
    cell_mask = ((x // grid_size) + (y // grid_size)) % 2 == 0

    checker = np.zeros_like(warped_ref)
    checker[mask_ref] = warped_ref[mask_ref]
    checker[mask_src] = warped_src[mask_src]
    checker[mask_overlap & cell_mask] = warped_ref[mask_overlap & cell_mask]
    checker[mask_overlap & ~cell_mask] = warped_src[mask_overlap & ~cell_mask]

    return checker


def make_professional_suite(
    warped_source: np.ndarray,
    reference: np.ndarray,
    mask_overlap: np.ndarray | None = None,
    grid_size: int = 45,
    out_path: str | Path | None = None,
    title_suffix: str = "",
) -> np.ndarray:
    """
    Generate a publication-grade 4-panel visual verification suite:
      1. Seamless Checkerboard (zero cuts/seams)
      2. 50/50 Alpha Blend Overlay
      3. Canny Edge Alignment (cyan LRO contours over OHRC)
      4. False-Color Multi-Modal Alignment (R=OHRC, G=LRO, B=OHRC)

    Parameters
    ----------
    warped_source : ndarray (H, W) uint8 — source warped into reference space
    reference     : ndarray (H, W) uint8 — reference image
    mask_overlap  : ndarray (H, W) bool — optional overlap mask; if None, derived from >0
    grid_size     : int — checkerboard square size
    out_path      : str or Path — path to save the high-resolution PNG
    title_suffix  : str — optional subtitle string

    Returns
    -------
    suite_rgb : ndarray (H_suite, W_suite, 3) uint8
    """
    if mask_overlap is None:
        mask_overlap = (warped_source > 0) & (reference > 0)

    y_idx, x_idx = np.where(mask_overlap)
    if len(y_idx) == 0:
        ymin, ymax, xmin, xmax = 0, reference.shape[0], 0, reference.shape[1]
    else:
        ymin, ymax = y_idx.min(), y_idx.max()
        xmin, xmax = x_idx.min(), x_idx.max()

    src_c = warped_source[ymin:ymax, xmin:xmax]
    ref_c = reference[ymin:ymax, xmin:xmax]
    mask_c = mask_overlap[ymin:ymax, xmin:xmax]
    ch_h, ch_w = src_c.shape

    # 1. Seamless Checkerboard
    checker = np.copy(src_c)
    for y in range(0, ch_h, grid_size):
        for x in range(0, ch_w, grid_size):
            if ((x // grid_size) + (y // grid_size)) % 2 == 0:
                y2 = min(y + grid_size, ch_h)
                x2 = min(x + grid_size, ch_w)
                sub_m = mask_c[y:y2, x:x2]
                checker[y:y2, x:x2][sub_m] = ref_c[y:y2, x:x2][sub_m]

    # 2. 50/50 Alpha Blend
    blend = (src_c.astype(np.float32) * 0.5 + ref_c.astype(np.float32) * 0.5).astype(
        np.uint8
    )

    # 3. Canny Edge Contours
    edges_ref = cv2.Canny(ref_c, 50, 150)
    edge_vis = cv2.cvtColor(src_c, cv2.COLOR_GRAY2RGB)
    edge_vis[edges_ref > 0] = [0, 255, 255]  # Cyan contours for LRO

    # 4. False-Color Multi-Modal Composite
    false_color = np.stack([src_c, ref_c, src_c], axis=-1)

    fig, axes = plt.subplots(1, 4, figsize=(22, 10))
    fig.patch.set_facecolor("#0d1117")

    panels = [
        (checker, "1. Seamless Checkerboard (Zero Seams)", "gray"),
        (blend, "2. 50/50 Alpha Blend Overlay", "gray"),
        (edge_vis, "3. Canny Edge Alignment (LRO cyan contours)", None),
        (false_color, "4. Multi-Modal Alignment (R/B: OHRC, G: LRO)", None),
    ]

    for ax, (img, title, cmap) in zip(axes, panels):
        ax.set_facecolor("#161b22")
        if cmap:
            ax.imshow(img, cmap=cmap)
        else:
            ax.imshow(img)
        ax.set_title(title, color="white", fontsize=11, fontweight="bold", pad=8)
        ax.axis("off")

    main_title = "LunarCV Breakthrough: Continuous Multi-Modal Registration"
    if title_suffix:
        main_title += f" — {title_suffix}"
    fig.suptitle(main_title, color="white", fontsize=15, fontweight="bold", y=0.98)
    plt.tight_layout()

    if out_path is not None:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(
            out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor()
        )

    # Canvas to RGB array
    fig.canvas.draw()
    try:
        rgba = np.asarray(fig.canvas.buffer_rgba())
        suite_rgb = cv2.cvtColor(rgba, cv2.COLOR_RGBA2RGB)
    except AttributeError:
        suite_rgb = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        suite_rgb = suite_rgb.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    plt.close(fig)

    return suite_rgb


# ---------------------------------------------------------------------------
# One-shot registration helper (legacy & standalone compatibility)
# ---------------------------------------------------------------------------


def compute_registration(
    ref_img: np.ndarray,
    src_img: np.ndarray,
    pts_ref: np.ndarray,
    pts_src: np.ndarray,
    max_canvas: int = 20_000,
    checkerboard_grid_size: int = 50,
    model: str = "affine",
) -> RegistrationResult | None:
    """
    Full registration pipeline for a single image pair:
      1. Estimate transform (ref → src) from refined inlier correspondences.
      2. Compute the warped bounding box of the reference image.
      3. Build translation T to place the warped region at canvas origin.
      4. Warp both images; compute masks.
      5. Build overlay and checkerboard composites.
    """
    H = estimate_transform(pts_ref, pts_src, model=model)
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
