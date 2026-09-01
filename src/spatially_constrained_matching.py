"""
spatially_constrained_matching.py

Runs the complete spatially constrained matching experiment on the 
OHRC ↔ LRO NAC pair. Reuses serialized LoFTR output for speed.

Experiments:
  A: Current baseline (Raw matches -> MAGSAC++)
  B: Confidence filtering only
  C: Spatial uniformity only
  D: Confidence + Spatial uniformity

Evaluates multiple transform models (Similarity, Affine, Homography).
Saves metrics to outputs/metrics/spatial_matching_comparison.json and .csv.
"""

from __future__ import annotations

import sys
import json
import pandas as pd
from pathlib import Path
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    OHRC_IMG_PATH, OHRC_DTYPE,
    LRO_IMG_PATH, SCALE_RATIO_LRO_TO_OHRC,
    FIGURES_DIR, MATCHES_PROCESSED_DIR
)
from matching import (
    load_matching_images,
    prepare_matching_pair,
    LoFTRMatcher,
    save_matches_npz,
    load_matches_npz,
    filter_match_confidence
)
from spatial_uniformity import filter_spatial_uniformity
from transform import estimate_transform
from evaluate import calculate_reprojection_errors, calculate_spatial_metrics, cross_validate_transform
def draw_connected_matches(
    img_src: np.ndarray,
    img_ref: np.ndarray,
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    save_path: Path,
    title: str = "Feature Correspondences",
) -> None:
    """Draw side-by-side matching figure with colored connecting lines."""
    h_src, w_src = img_src.shape
    h_ref, w_ref = img_ref.shape

    canvas_h = max(h_src, h_ref)
    canvas_w = w_src + w_ref

    fig, ax = plt.subplots(figsize=(16, 10))
    canvas = np.zeros((canvas_h, canvas_w), dtype=np.uint8)

    canvas[:h_src, :w_src] = img_src
    canvas[:h_ref, w_src:w_src + w_ref] = img_ref

    ax.imshow(canvas, cmap="gray")
    ax.set_title(title, fontsize=13, fontweight="bold")

    colors = plt.cm.rainbow(np.linspace(0, 1, max(1, len(pts_src))))
    for i, (p_src, p_ref) in enumerate(zip(pts_src, pts_ref)):
        x1, y1 = p_src[0], p_src[1]
        x2, y2 = p_ref[0] + w_src, p_ref[1]
        c = colors[i]

        ax.plot([x1, x2], [y1, y2], color=c, linewidth=1.2, alpha=0.8)
        ax.scatter([x1, x2], [y1, y2], color=c, s=20, zorder=3)

    ax.set_xlim(0, canvas_w)
    ax.set_ylim(canvas_h, 0)
    ax.axis("off")

    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [fig] Saved match figure -> {save_path}")


def ensure_raw_matches_exist(
    src_raw: np.ndarray,
    ref_raw: np.ndarray,
    npz_path: Path
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Load or generate the base LoFTR candidates to speed up iteration."""
    src_scaled, ref_norm = prepare_matching_pair(src_raw, ref_raw, SCALE_RATIO_LRO_TO_OHRC)
    
    if npz_path.exists():
        print(f"Loading cached matches from {npz_path}...")
        pts_src, pts_ref, conf, meta = load_matches_npz(npz_path)
    else:
        print(f"Running LoFTR inference (no cache found at {npz_path})...")
        matcher = LoFTRMatcher(pretrained="outdoor", max_dim=1024)
        pts_src, pts_ref, conf = matcher.match(src_scaled, ref_norm, conf_threshold=0.0)
        save_matches_npz(npz_path, pts_src, pts_ref, conf, {"scale_ratio": SCALE_RATIO_LRO_TO_OHRC})
        
    return src_scaled, ref_norm, pts_src, pts_ref, conf


def run_single_experiment(
    exp_name: str,
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    conf: np.ndarray,
    image_shape: tuple[int, int],
    model: str = "homography",
    threshold: float = 4.0
) -> dict:
    """Run outlier rejection, metrics, and CV for a set of candidates."""
    # 1. Transform Estimation
    M, mask = estimate_transform(pts_src, pts_ref, model=model, ransac_reproj_threshold=threshold)
    
    inliers_src = pts_src[mask]
    inliers_ref = pts_ref[mask]
    
    if M is None or len(inliers_src) < 4:
        return {
            "Experiment": exp_name, "Model": model,
            "Candidates": len(pts_src), "Inliers": len(inliers_src), "Inlier_Ratio": 0.0,
            "Fwd_RMSE": np.nan, "Bwd_RMSE": np.nan, "Sym_RMSE": np.nan,
            "CV_RMSE": np.nan, "Hull_Coverage": 0.0, "Grid_Occupancy": 0.0,
            "Status": "FAILED"
        }

    inlier_ratio = len(inliers_src) / len(pts_src)
    
    # 2. Geometric Errors
    err_metrics = calculate_reprojection_errors(inliers_src, inliers_ref, M)
    
    # 3. Spatial Metrics
    sp_metrics = calculate_spatial_metrics(inliers_src, image_shape, grid_size=(4, 4))
    
    # 4. Cross Validation
    cv_metrics = cross_validate_transform(inliers_src, inliers_ref, model=model, threshold=threshold)
    
    return {
        "Experiment": exp_name,
        "Model": model,
        "Candidates": len(pts_src),
        "Inliers": len(inliers_src),
        "Inlier_Ratio": inlier_ratio * 100.0,
        "Fwd_RMSE": err_metrics["fwd_rmse"],
        "Bwd_RMSE": err_metrics["bwd_rmse"],
        "Sym_RMSE": err_metrics["sym_rmse"],
        "CV_RMSE": cv_metrics["cv_rmse"],
        "Hull_Coverage": sp_metrics["hull_coverage"],
        "Grid_Occupancy": sp_metrics["grid_occupancy"],
        "Status": "SUCCESS"
    }


def draw_spatially_uniform_occupancy(
    img: np.ndarray,
    pts: np.ndarray,
    grid_size: tuple[int, int],
    save_path: Path
):
    """Draw a 4x4 grid overlay and plot points to visualize occupancy."""
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(img, cmap="gray")
    
    h, w = img.shape
    r_step = h / grid_size[0]
    c_step = w / grid_size[1]
    
    for r in range(1, grid_size[0]):
        ax.axhline(r * r_step, color="yellow", alpha=0.5, linestyle="--")
    for c in range(1, grid_size[1]):
        ax.axvline(c * c_step, color="yellow", alpha=0.5, linestyle="--")
        
    ax.scatter(pts[:, 0], pts[:, 1], c='red', s=20, marker='o')
    ax.set_title(f"Spatial Occupancy ({len(pts)} points)")
    ax.axis('off')
    
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def create_overlays(
    src_img: np.ndarray,
    ref_img: np.ndarray,
    M: np.ndarray,
    save_prefix: str
):
    """Generate Alpha blended and Checkerboard warped overlays."""
    # M maps Ref -> Src. To warp Src onto Ref, we need M_inv.
    try:
        M_inv = np.linalg.inv(M)
    except np.linalg.LinAlgError:
        print("Cannot create overlays: M is singular.")
        return
        
    warped_src = cv2.warpPerspective(src_img, M_inv, (ref_img.shape[1], ref_img.shape[0]))
    
    # Alpha Overlay
    alpha = 0.5
    overlay = cv2.addWeighted(ref_img, alpha, warped_src, 1 - alpha, 0)
    cv2.imwrite(f"{save_prefix}_alpha.png", overlay)
    
    # Checkerboard Overlay
    checker_size = 150
    checker = ref_img.copy()
    h, w = ref_img.shape
    for y in range(0, h, checker_size):
        for x in range(0, w, checker_size):
            if ((x // checker_size) + (y // checker_size)) % 2 == 1:
                y_end = min(y + checker_size, h)
                x_end = min(x + checker_size, w)
                checker[y:y_end, x:x_end] = warped_src[y:y_end, x:x_end]
                
    cv2.imwrite(f"{save_prefix}_checker.png", checker)


def main():
    print("=" * 80)
    print("SPATIALLY CONSTRAINED MATCHING EXPERIMENT")
    print("=" * 80)
    
    METRICS_DIR = Path("outputs/metrics")
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Data
    ohrc_bounds = ((30000, 45000), (2000, 8000))
    lro_bounds = ((5500, 8500), (400, 1800))
    
    src_raw, ref_raw = load_matching_images(OHRC_IMG_PATH, LRO_IMG_PATH, ohrc_bounds, lro_bounds)
    
    # 2. Get Raw Candidates
    npz_path = MATCHES_PROCESSED_DIR / "raw_candidates.npz"
    src_img, ref_img, raw_src, raw_ref, raw_conf = ensure_raw_matches_exist(src_raw, ref_raw, npz_path)
    image_shape = src_img.shape
    print(f"Base Candidates: {len(raw_src)}")
    
    results = []
    
    # ==========================================
    # EXPERIMENT A: Baseline (No constraints)
    # ==========================================
    res_A = run_single_experiment("A_Baseline", raw_src, raw_ref, raw_conf, image_shape, "homography")
    results.append(res_A)
    
    # ==========================================
    # EXPERIMENT B: Confidence Filtering Sweep
    # ==========================================
    for conf_th in [0.20, 0.30, 0.40, 0.50]:
        f_src, f_ref, f_conf = filter_match_confidence(raw_src, raw_ref, raw_conf, conf_th)
        res_B = run_single_experiment(f"B_Conf_{conf_th:.2f}", f_src, f_ref, f_conf, image_shape, "homography")
        results.append(res_B)
        
    # ==========================================
    # EXPERIMENT C: Spatial Uniformity Only
    # ==========================================
    sp_src, sp_ref, sp_conf, _ = filter_spatial_uniformity(
        raw_src, raw_ref, raw_conf, image_shape, grid_size=(4, 4), top_k_per_cell=5, min_conf=0.0
    )
    res_C = run_single_experiment("C_Spatial_Only", sp_src, sp_ref, sp_conf, image_shape, "homography")
    results.append(res_C)
    
    # ==========================================
    # EXPERIMENT D: Confidence + Spatial Uniformity
    # ==========================================
    # We will test multiple top_K and models on a reasonable confidence floor
    for model in ["similarity", "affine", "homography"]:
        f_src, f_ref, f_conf, _ = filter_spatial_uniformity(
            raw_src, raw_ref, raw_conf, image_shape, grid_size=(4, 4), top_k_per_cell=10, min_conf=0.20
        )
        res_D = run_single_experiment(f"D_Conf_Spatial_{model.capitalize()}", f_src, f_ref, f_conf, image_shape, model)
        results.append(res_D)
        
    # ==========================================
    # SAVE AND PRINT RESULTS
    # ==========================================
    df = pd.DataFrame(results)
    csv_path = METRICS_DIR / "spatial_matching_comparison.csv"
    json_path = METRICS_DIR / "spatial_matching_comparison.json"
    
    df.to_csv(csv_path, index=False, float_format='%.3f')
    df.to_json(json_path, orient="records", indent=4)
    
    print("\n--- EXPERIMENT RESULTS ---")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 150)
    print(df[["Experiment", "Model", "Candidates", "Inliers", "Grid_Occupancy", "Hull_Coverage", "Sym_RMSE", "CV_RMSE"]])
    
    # ==========================================
    # VISUALIZATION FOR BEST EXPERIMENT (D Homography)
    # ==========================================
    best_src, best_ref, best_conf, _ = filter_spatial_uniformity(
        raw_src, raw_ref, raw_conf, image_shape, grid_size=(4, 4), top_k_per_cell=10, min_conf=0.20
    )
    M_best, mask_best = estimate_transform(best_src, best_ref, model="homography")
    
    if M_best is not None:
        inliers_src = best_src[mask_best]
        inliers_ref = best_ref[mask_best]
        
        # 1. Spatial Occupancy Plot
        draw_spatially_uniform_occupancy(src_img, inliers_src, (4, 4), FIGURES_DIR / "expD_spatial_occupancy.png")
        
        # 2. Match connections
        draw_connected_matches(src_img, ref_img, inliers_src, inliers_ref, FIGURES_DIR / "expD_matches.png", 
                               title=f"Exp D (Conf+Spatial) Matches - {len(inliers_src)} inliers")
                               
        # 3. Overlays
        create_overlays(src_img, ref_img, M_best, str(FIGURES_DIR / "expD_overlay"))
        print("\nGenerated visualization figures in outputs/figures/")

if __name__ == "__main__":
    main()
