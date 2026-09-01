"""
analyze_inliers_ohrc_lro.py
Script to analyze the 13 MAGSAC++ inliers from the OHRC-LRO NAC registration.
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
from scipy.spatial.distance import pdist, squareform
from sklearn.model_selection import KFold

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    OHRC_IMG_PATH, OHRC_SHAPE, OHRC_DTYPE,
    LRO_IMG_PATH, SCALE_RATIO_LRO_TO_OHRC,
    FIGURES_DIR, MATCHES_PROCESSED_DIR
)
from io_utils import load_ohrc_memmap, load_lro_nac_memmap, extract_patch
def percentile_stretch_uint8(img: np.ndarray, p_low: float = 1.0, p_high: float = 99.0) -> np.ndarray:
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    stretched = np.clip((img.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255)
    return stretched.astype(np.uint8)


def main():
    print("=" * 70)
    print("INLIER ANALYSIS: OHRC <-> LRO NAC")
    print("=" * 70)
    
    # Load points and homography
    try:
        pts_src = np.load(MATCHES_PROCESSED_DIR / "ohrc_lro_mkpts_src.npy")
        pts_ref = np.load(MATCHES_PROCESSED_DIR / "ohrc_lro_mkpts_ref.npy")
        H = np.load(MATCHES_PROCESSED_DIR / "ohrc_lro_H.npy")
    except FileNotFoundError as e:
        print(f"Error loading saved matches: {e}")
        return

    n_points = len(pts_src)
    print(f"Loaded {n_points} inliers.")

    # 1. Print every inlier's coordinates
    print("\n1. INLIER COORDINATES (x, y):")
    for i in range(n_points):
        print(f"  Point {i:2d}: Src ({pts_src[i, 0]:.1f}, {pts_src[i, 1]:.1f}) -> Ref ({pts_ref[i, 0]:.1f}, {pts_ref[i, 1]:.1f})")

    # Load images for visualization
    print("\nLoading image patches...")
    ohrc_mm = load_ohrc_memmap(OHRC_IMG_PATH, shape=OHRC_SHAPE, dtype=OHRC_DTYPE)
    lro_mm, _ = load_lro_nac_memmap(LRO_IMG_PATH)
    
    ohrc_raw = extract_patch(ohrc_mm, (30000, 45000), (2000, 8000))
    lro_raw = extract_patch(lro_mm, (5500, 8500), (400, 1800))
    
    ohrc_norm = percentile_stretch_uint8(ohrc_raw)
    lro_norm = percentile_stretch_uint8(lro_raw)
    
    target_w = int(round(ohrc_norm.shape[1] / SCALE_RATIO_LRO_TO_OHRC))
    target_h = int(round(ohrc_norm.shape[0] / SCALE_RATIO_LRO_TO_OHRC))
    ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)

    # 2 & 3. Plot points alone
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    ax1.imshow(ohrc_scaled, cmap="gray")
    ax1.scatter(pts_src[:, 0], pts_src[:, 1], c='red', s=40, marker='x')
    ax1.set_title("Source (OHRC) Inliers")
    
    ax2.imshow(lro_norm, cmap="gray")
    ax2.scatter(pts_ref[:, 0], pts_ref[:, 1], c='blue', s=40, marker='x')
    ax2.set_title("Reference (LRO NAC) Inliers")
    
    plot_path = FIGURES_DIR / "inlier_locations.png"
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n2 & 3. Saved locations plot to {plot_path}")

    # 4. 4x4 Grid Occupancy on Source
    h_src, w_src = ohrc_scaled.shape
    grid_size = 4
    grid = np.zeros((grid_size, grid_size), dtype=int)
    for p in pts_src:
        gx = int(p[0] / w_src * grid_size)
        gy = int(p[1] / h_src * grid_size)
        gx = min(gx, grid_size - 1)
        gy = min(gy, grid_size - 1)
        grid[gy, gx] += 1
    
    occupied = np.count_nonzero(grid)
    print("\n4. 4x4 GRID OCCUPANCY (Source):")
    print(grid)
    print(f"  Occupied cells: {occupied}/16 ({occupied/16*100:.1f}%)")

    # 5. Convex Hull Coverage
    print("\n5. CONVEX HULL COVERAGE:")
    try:
        hull = ConvexHull(pts_src)
        hull_area = hull.volume
        total_area = w_src * h_src
        coverage = hull_area / total_area * 100
        print(f"  Hull area: {hull_area:.0f} px^2")
        print(f"  Total area: {total_area:.0f} px^2")
        print(f"  Coverage: {coverage:.2f}%")
    except Exception as e:
        print(f"  Could not compute convex hull: {e}")

    # 6. Nearest Neighbor and Minimum Pairwise Distances
    print("\n6. PAIRWISE DISTANCES (Source):")
    dist_matrix = squareform(pdist(pts_src))
    np.fill_diagonal(dist_matrix, np.inf)
    min_dist_per_point = np.min(dist_matrix, axis=1)
    
    print(f"  Min pairwise distance: {np.min(dist_matrix):.2f} px")
    print(f"  Max pairwise distance: {np.max(dist_matrix[dist_matrix != np.inf]):.2f} px")
    print(f"  Median nearest neighbor: {np.median(min_dist_per_point):.2f} px")

    # 7. Check for groups with similar displacement vectors
    print("\n7. DISPLACEMENT VECTORS (Ref - Src):")
    displacements = pts_ref - pts_src
    for i, d in enumerate(displacements):
        print(f"  Vector {i:2d}: ({d[0]:6.1f}, {d[1]:6.1f})  Magnitude: {np.linalg.norm(d):.1f}")
    
    mean_disp = np.mean(displacements, axis=0)
    std_disp = np.std(displacements, axis=0)
    print(f"  Mean Displacement: ({mean_disp[0]:.1f}, {mean_disp[1]:.1f})")
    print(f"  Std Dev Displacement: ({std_disp[0]:.1f}, {std_disp[1]:.1f})")

    # 8. Transfer errors
    print("\n8. TRANSFER ERRORS:")
    
    def transform_points(pts, homography):
        pts_3d = np.concatenate([pts, np.ones((len(pts), 1))], axis=1)
        pred_3d = (homography @ pts_3d.T).T
        pred_2d = pred_3d[:, :2] / pred_3d[:, 2:]
        return pred_2d

    H_inv = np.linalg.inv(H)
    
    pred_src = transform_points(pts_ref, H)
    fwd_errors = np.linalg.norm(pts_src - pred_src, axis=1)
    
    pred_ref = transform_points(pts_src, H_inv)
    bwd_errors = np.linalg.norm(pts_ref - pred_ref, axis=1)
    
    sym_errors = (fwd_errors**2 + bwd_errors**2)
    
    print(f"  Forward RMSE (Src->Ref)  : {np.sqrt(np.mean(fwd_errors**2)):.4f} px")
    print(f"  Backward RMSE (Ref->Src) : {np.sqrt(np.mean(bwd_errors**2)):.4f} px")
    print(f"  Symmetric RMSE           : {np.sqrt(np.mean(sym_errors)):.4f} px")

    # 9. 5-Fold Cross Validation
    print("\n9. 5-FOLD CROSS VALIDATION:")
    if n_points >= 5:
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_errors = []
        for train_idx, test_idx in kf.split(pts_src):
            train_src, test_src = pts_src[train_idx], pts_src[test_idx]
            train_ref, test_ref = pts_ref[train_idx], pts_ref[test_idx]
            
            H_cv, _ = cv2.findHomography(train_src, train_ref, cv2.RANSAC, 4.0)
            if H_cv is not None:
                pred_test = transform_points(test_src, H_cv)
                errs = np.linalg.norm(test_ref - pred_test, axis=1)
                cv_errors.extend(errs)
        
        if cv_errors:
            cv_rmse = np.sqrt(np.mean(np.array(cv_errors)**2))
            print(f"  CV Reprojection RMSE: {cv_rmse:.4f} px")
        else:
            print("  CV failed to fit homography.")
    else:
        print("  Not enough points for 5-fold CV.")

    # 10. Warped Overlays
    print("\n10. GENERATING OVERLAYS:")
    warped_ohrc = cv2.warpPerspective(ohrc_scaled, H, (lro_norm.shape[1], lro_norm.shape[0]))
    
    alpha = 0.5
    overlay = cv2.addWeighted(lro_norm, alpha, warped_ohrc, 1 - alpha, 0)
    overlay_path = FIGURES_DIR / "inlier_alpha_overlay.png"
    cv2.imwrite(str(overlay_path), overlay)
    print(f"  Saved alpha overlay to {overlay_path}")
    
    checker_size = 150
    checker = lro_norm.copy()
    h, w = lro_norm.shape
    for y in range(0, h, checker_size):
        for x in range(0, w, checker_size):
            if ((x // checker_size) + (y // checker_size)) % 2 == 1:
                y_end = min(y + checker_size, h)
                x_end = min(x + checker_size, w)
                checker[y:y_end, x:x_end] = warped_ohrc[y:y_end, x:x_end]
                
    checker_path = FIGURES_DIR / "inlier_checker_overlay.png"
    cv2.imwrite(str(checker_path), checker)
    print(f"  Saved checkerboard overlay to {checker_path}")


if __name__ == "__main__":
    main()
