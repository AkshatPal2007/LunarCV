"""
preprocessing.py — Core image preprocessing utilities for LunarCV.

Functions:
    normalize_uint16_to_uint8 — Percentile-based stretch of a uint16 patch to uint8.
    apply_clahe               — Contrast-Limited Adaptive Histogram Equalisation via OpenCV.
    save_comparison_figure    — Side-by-side matplotlib figure of two images with colorbars.
    save_single_figure        — Single-panel figure helper.

Notes:
    - All functions operate on NumPy ndarrays (2-D, single channel).
    - GPU tensors are NOT used here; conversions happen before this layer.
    - Phase Congruency is deferred to a future module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import matplotlib
matplotlib.use("Agg")          # non-interactive backend — safe in scripts
import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_uint16_to_uint8(
    patch: np.ndarray,
    p_low: float = 2.0,
    p_high: float = 98.0,
) -> np.ndarray:
    """
    Percentile-clip and linearly rescale a uint16 array to uint8 [0, 255].

    Parameters
    ----------
    patch : ndarray, dtype uint16 or float
        Input image patch.  Shape: (H, W).
    p_low : float
        Lower percentile used for the stretch floor (default 2 %).
    p_high : float
        Upper percentile used for the stretch ceiling (default 98 %).

    Returns
    -------
    ndarray, dtype uint8, shape (H, W)
        Contrast-stretched image ready for CLAHE or display.
    """
    if patch.ndim != 2:
        raise ValueError(f"Expected a 2-D array, got shape {patch.shape}")

    v_low = float(np.percentile(patch, p_low))
    v_high = float(np.percentile(patch, p_high))

    if v_high <= v_low:
        # Flat or near-flat patch — return zeros rather than divide-by-zero
        return np.zeros(patch.shape, dtype=np.uint8)

    # Clip + rescale to [0.0, 255.0] and cast
    clipped = np.clip(patch.astype(np.float32), v_low, v_high)
    scaled = (clipped - v_low) / (v_high - v_low) * 255.0
    return scaled.astype(np.uint8)


# -----------------------------
# CLAHE
# -----------------------------

def apply_clahe(
    image_u8: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: tuple = (8, 8),
) -> np.ndarray:
    """
    Apply OpenCV CLAHE to an 8-bit single-channel image.

    Parameters
    ----------
    image_u8 : ndarray, dtype uint8
        Input image.  Must be 2-D and uint8 (call normalize_uint16_to_uint8 first).
    clip_limit : float
        CLAHE clip limit — threshold for contrast limiting (default 2.0).
        Higher values allow more contrast amplification but risk noise boost.
    tile_grid_size : (int, int)
        Number of tiles in (x, y) for the adaptive histogram (default 8x8).

    Returns
    -------
    ndarray, dtype uint8, shape identical to input
        CLAHE-enhanced image.
    """
    if image_u8.dtype != np.uint8:
        raise TypeError(
            f"apply_clahe expects uint8 input, got {image_u8.dtype}. "
            "Call normalize_uint16_to_uint8 first."
        )
    if image_u8.ndim != 2:
        raise ValueError(f"Expected a 2-D array, got shape {image_u8.shape}")

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(image_u8)



# Visualization helpers
def save_comparison_figure(
    img_left: np.ndarray,
    img_right: np.ndarray,
    title_left: str,
    title_right: str,
    save_path: Path,
    suptitle: Optional[str] = None,
    cmap: str = "gray",
    dpi: int = 150,
) -> None:
    """
    Save a side-by-side comparison of two single-channel images to disk.

    Parameters
    ----------
    img_left, img_right : ndarray
        Images to compare.  Must be 2-D.
    title_left, title_right : str
        Per-panel titles.
    save_path : Path
        Destination file (.png recommended).
    suptitle : str, optional
        Figure-level super-title.
    cmap : str
        Matplotlib colormap (default 'gray').
    dpi : int
        Output resolution (default 150).
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), constrained_layout=True)

    im0 = axes[0].imshow(img_left, cmap=cmap, interpolation="nearest")
    axes[0].set_title(title_left, fontsize=12)
    axes[0].axis("off")
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(img_right, cmap=cmap, interpolation="nearest")
    axes[1].set_title(title_right, fontsize=12)
    axes[1].axis("off")
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    if suptitle:
        fig.suptitle(suptitle, fontsize=14, fontweight="bold")

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig] Saved comparison figure -> {save_path}")


def save_single_figure(
    image: np.ndarray,
    title: str,
    save_path: Path,
    cmap: str = "gray",
    dpi: int = 150,
) -> None:
    """
    Save a single-panel figure of one image to disk.

    Parameters
    ----------
    image : ndarray
        2-D image array.
    title : str
        Panel title (also used as the figure title).
    save_path : Path
        Destination file path.
    cmap : str
        Matplotlib colormap (default 'gray').
    dpi : int
        Output resolution (default 150).
    """
    fig, ax = plt.subplots(figsize=(8, 7), constrained_layout=True)
    im = ax.imshow(image, cmap=cmap, interpolation="nearest")
    ax.set_title(title, fontsize=12)
    ax.axis("off")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig] Saved figure -> {save_path}")
