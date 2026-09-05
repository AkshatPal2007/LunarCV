"""
spatial_uniformity.py — Grid-based spatial distribution analysis and filtering for LunarCV.

Per CLAUDE.md architecture:
  MAGSAC++ runs BEFORE grid-based spatial distribution — reject geometrically
  wrong matches first, then enforce spatial coverage on the clean set.

Provides:
  - grid_occupancy()           : measure how many grid cells contain at least one match
  - convex_hull_coverage()     : convex hull area of matches as % of image area
  - min_pairwise_separation()  : minimum inter-point distance (avoids clustering)
  - spatial_topk_filter()      : retain best-confidence match per grid cell (top-K)
  - spatial_uniformity_report(): print full uniformity stats dict

All functions operate on (x, y) float32 Nx2 arrays in image pixel coordinates.
"""

from __future__ import annotations

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Grid Occupancy
# ---------------------------------------------------------------------------


def grid_occupancy(
    pts: np.ndarray,
    image_h: int,
    image_w: int,
    n_rows: int = 4,
    n_cols: int = 4,
) -> dict:
    """
    Measure how many grid cells contain at least one correspondence point.

    Parameters
    ----------
    pts : ndarray (N, 2) — (x, y) match coordinates in image pixels
    image_h, image_w : int — full image dimensions (height, width)
    n_rows, n_cols : int — number of grid rows and columns

    Returns
    -------
    dict with keys:
        occupied_cells : int
        total_cells    : int
        occupancy_pct  : float [0, 100]
        grid_counts    : ndarray (n_rows, n_cols) — match count per cell
    """
    total_cells = n_rows * n_cols
    grid_counts = np.zeros((n_rows, n_cols), dtype=int)

    if len(pts) == 0:
        return {
            "occupied_cells": 0,
            "total_cells": total_cells,
            "occupancy_pct": 0.0,
            "grid_counts": grid_counts,
        }

    cell_h = image_h / n_rows
    cell_w = image_w / n_cols

    for x, y in pts:
        row = int(min(y // cell_h, n_rows - 1))
        col = int(min(x // cell_w, n_cols - 1))
        grid_counts[row, col] += 1

    occupied = int((grid_counts > 0).sum())
    return {
        "occupied_cells": occupied,
        "total_cells": total_cells,
        "occupancy_pct": 100.0 * occupied / total_cells,
        "grid_counts": grid_counts,
    }


# ---------------------------------------------------------------------------
# Convex Hull Coverage
# ---------------------------------------------------------------------------


def convex_hull_coverage(
    pts: np.ndarray,
    image_h: int,
    image_w: int,
) -> float:
    """
    Compute convex hull area of the match points as a percentage of image area.

    Parameters
    ----------
    pts : ndarray (N, 2) — (x, y) match coordinates
    image_h, image_w : int — full image dimensions

    Returns
    -------
    float : hull area / image area * 100  [0.0 – 100.0]
    """
    image_area = float(image_h * image_w)
    if image_area <= 0:
        return 0.0
    if len(pts) < 3:
        return 0.0

    hull = cv2.convexHull(pts.astype(np.float32))
    hull_area = float(cv2.contourArea(hull))
    return min(100.0, hull_area / image_area * 100.0)


# ---------------------------------------------------------------------------
# Minimum Pairwise Separation
# ---------------------------------------------------------------------------


def min_pairwise_separation(pts: np.ndarray) -> float:
    """
    Compute the minimum Euclidean distance between any two match points.
    Returns 0.0 when fewer than 2 points exist.

    Parameters
    ----------
    pts : ndarray (N, 2) — (x, y) match coordinates

    Returns
    -------
    float : minimum inter-point distance in pixels
    """
    if len(pts) < 2:
        return 0.0

    min_dist = np.inf
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = float(np.linalg.norm(pts[i] - pts[j]))
            if d < min_dist:
                min_dist = d
    return min_dist


# ---------------------------------------------------------------------------
# Spatially Distributed Top-K Filter
# ---------------------------------------------------------------------------


def spatial_topk_filter(
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    conf: np.ndarray | None,
    image_h: int,
    image_w: int,
    n_rows: int = 4,
    n_cols: int = 4,
    top_k_per_cell: int = 2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """
    Select the top-K highest-confidence matches per grid cell, enforcing
    spatial distribution across the image.

    MAGSAC++ must be run BEFORE this function. This function enforces coverage
    on the already-clean set (per CLAUDE.md architecture order).

    Parameters
    ----------
    pts_src : ndarray (N, 2) — source image (x, y) coordinates
    pts_ref : ndarray (N, 2) — reference image (x, y) coordinates
    conf    : ndarray (N,) | None — per-match confidence scores; if None, all equal
    image_h, image_w : int — source image dimensions
    n_rows, n_cols : int — grid subdivision
    top_k_per_cell : int — max matches to keep per grid cell

    Returns
    -------
    pts_src_filtered : ndarray (M, 2)
    pts_ref_filtered : ndarray (M, 2)
    conf_filtered    : ndarray (M,) | None
    """
    n = len(pts_src)
    if n == 0:
        return pts_src.copy(), pts_ref.copy(), conf.copy() if conf is not None else None

    scores = conf if conf is not None else np.ones(n, dtype=np.float32)

    cell_h = image_h / n_rows
    cell_w = image_w / n_cols

    # Assign each point to a grid cell
    cell_indices: dict[tuple[int, int], list[int]] = {}
    for idx, (x, y) in enumerate(pts_src):
        row = int(min(y // cell_h, n_rows - 1))
        col = int(min(x // cell_w, n_cols - 1))
        cell_indices.setdefault((row, col), []).append(idx)

    kept = []
    for cell_pts in cell_indices.values():
        # Sort by descending confidence
        cell_pts_sorted = sorted(cell_pts, key=lambda i: scores[i], reverse=True)
        kept.extend(cell_pts_sorted[:top_k_per_cell])

    kept = np.array(kept, dtype=int)
    pts_src_f = pts_src[kept]
    pts_ref_f = pts_ref[kept]
    conf_f = scores[kept] if conf is not None else None

    return pts_src_f, pts_ref_f, conf_f


# ---------------------------------------------------------------------------
# Full Uniformity Report
# ---------------------------------------------------------------------------


def spatial_uniformity_report(
    pts_src: np.ndarray,
    image_h: int,
    image_w: int,
    label: str = "matches",
    n_rows: int = 4,
    n_cols: int = 4,
) -> dict:
    """
    Compute and print all spatial uniformity metrics for a set of source points.

    Parameters
    ----------
    pts_src  : ndarray (N, 2) — source image (x, y) coordinates
    image_h, image_w : int — source image dimensions
    label    : str — label for print output
    n_rows, n_cols : int — grid subdivision

    Returns
    -------
    dict with:
        occupancy_pct      : float
        hull_coverage_pct  : float
        min_separation_px  : float
        grid_counts        : ndarray
    """
    occ = grid_occupancy(pts_src, image_h, image_w, n_rows, n_cols)
    hull_pct = convex_hull_coverage(pts_src, image_h, image_w)
    min_sep = min_pairwise_separation(pts_src)

    print(f"--- Spatial Uniformity [{label}] ---")
    print(
        f"  Grid ({n_rows}x{n_cols}): {occ['occupied_cells']}/{occ['total_cells']} cells occupied "
        f"({occ['occupancy_pct']:.1f}%)"
    )
    print(f"  Convex Hull Coverage : {hull_pct:.1f}% of source image area")
    print(f"  Min Point Separation : {min_sep:.1f} px")
    print(f"  Grid cell counts:\n{occ['grid_counts']}")

    return {
        "occupancy_pct": occ["occupancy_pct"],
        "hull_coverage_pct": hull_pct,
        "min_separation_px": min_sep,
        "grid_counts": occ["grid_counts"],
    }
