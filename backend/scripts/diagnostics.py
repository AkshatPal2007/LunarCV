import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lunarcv.config import (
    FIGURES_DIR, OHRC_IMG_PATH, OHRC_SHAPE, OHRC_DTYPE,
    LRO_IMG_PATH, LRO_SHAPE, LRO_DTYPE,
    SCALE_X_LRO_TO_OHRC, SCALE_Y_LRO_TO_OHRC
)
from lunarcv.io.raster import load_ohrc_memmap, load_lro_nac_memmap, extract_patch
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.registration.outlier_rejection import magsac_filter
from lunarcv.evaluation.metrics import calculate_rmse

def percentile_stretch_uint8(img: np.ndarray, p_low: float = 1.0, p_high: float = 99.0) -> np.ndarray:
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    stretched = np.clip((img.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255)
    return stretched.astype(np.uint8)

def main():
    print("Diagnostics: Part 1 and Part 2 checks")
    
    # Check 1: Image Dimensions and Assumptions
    ohrc_file_size = OHRC_IMG_PATH.stat().st_size
    lro_file_size = LRO_IMG_PATH.stat().st_size
    
    # We expect uint8 (1 byte per pixel)
    ohrc_expected_size = OHRC_SHAPE[0] * OHRC_SHAPE[1]
    lro_expected_size = LRO_SHAPE[0] * LRO_SHAPE[1]
    
    print("\n--- Part 2: Imagery Assumptions ---")
    print(f"OHRC File Size: {ohrc_file_size}, Expected (uint8): {ohrc_expected_size} -> Match: {ohrc_file_size == ohrc_expected_size}")
    print(f"LRO File Size: {lro_file_size}, Expected (uint8): {lro_expected_size} -> Match: {lro_file_size == lro_expected_size}")
    
    # Geographic crop verification
    ohrc_rows = (30000, 45000)
    print(f"Geographic Crop OHRC rows: {ohrc_rows}, Full OHRC rows: {OHRC_SHAPE[0]}")
    if ohrc_rows[1] - ohrc_rows[0] != OHRC_SHAPE[0]:
        print("  WARNING: Geographic crop does NOT cover the full OHRC strip.")

    # Load and process the images
    print("\n--- Part 1: Diagnostic Checks ---")
    
    # Using the exact same bounds as register_pair.py
    ohrc_mm = load_ohrc_memmap(OHRC_IMG_PATH, shape=OHRC_SHAPE, dtype=OHRC_DTYPE)
    lro_mm, lro_meta = load_lro_nac_memmap(LRO_IMG_PATH)
    
    ohrc_cols = (2000, 8000)
    lro_rows = (5500, 8500)
    lro_cols = (400, 1800)
    
    ohrc_raw = extract_patch(ohrc_mm, ohrc_rows, ohrc_cols)
    lro_raw = extract_patch(lro_mm, lro_rows, lro_cols)
    
    ohrc_norm = percentile_stretch_uint8(ohrc_raw)
    lro_norm = percentile_stretch_uint8(lro_raw)
    
    target_w = int(round(ohrc_norm.shape[1] / SCALE_X_LRO_TO_OHRC))
    target_h = int(round(ohrc_norm.shape[0] / SCALE_Y_LRO_TO_OHRC))
    ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)
    
    matcher = LightGlueFeatureMatcher(max_dim=1500, max_keypoints=2048)
    
    # Matching (in chunks like register_pair.py)
    n_chunks = 3
    overlap = 400
    h_src, w_src = ohrc_scaled.shape
    h_ref, w_ref = lro_norm.shape
    step_src = (h_src - overlap) // n_chunks
    step_ref = (h_ref - overlap) // n_chunks
    
    all_mkpts_src, all_mkpts_ref, all_conf = [], [], []
    for i in range(n_chunks):
        y1_src = i * step_src
        y2_src = y1_src + step_src + overlap if i < n_chunks - 1 else h_src
        y1_ref = i * step_ref
        y2_ref = y1_ref + step_ref + overlap if i < n_chunks - 1 else h_ref
        
        patch_src = ohrc_scaled[y1_src:y2_src, :]
        patch_ref = lro_norm[y1_ref:y2_ref, :]
        
        pts_src, pts_ref, conf = matcher.match(patch_src, patch_ref, conf_threshold=0.0)
        
        if len(pts_src) > 0:
            pts_src[:, 1] += y1_src
            pts_ref[:, 1] += y1_ref
            all_mkpts_src.append(pts_src)
            all_mkpts_ref.append(pts_ref)
            all_conf.append(conf)

    mkpts_src = np.vstack(all_mkpts_src)
    mkpts_ref = np.vstack(all_mkpts_ref)
    conf = np.concatenate(all_conf)
    
    print(f"Raw matches: {len(mkpts_src)}")
    
    mkpts_src_c, mkpts_ref_c, conf_c, H, mask = magsac_filter(
        mkpts_src, mkpts_ref, conf, model="homography", ransac_reproj_threshold=4.0
    )
    print(f"MAGSAC++ inliers: {len(mkpts_src_c)}")
    
    # 1. Plot inlier match locations
    fig, ax = plt.subplots(figsize=(8, 12))
    ax.imshow(ohrc_scaled, cmap='gray')
    ax.scatter(mkpts_src_c[:, 0], mkpts_src_c[:, 1], c='r', s=5, alpha=0.5)
    ax.set_title(f"Inlier Locations (Total: {len(mkpts_src_c)})")
    
    # Calculate span
    min_y = np.min(mkpts_src_c[:, 1])
    max_y = np.max(mkpts_src_c[:, 1])
    span = max_y - min_y
    span_fraction = span / h_src
    print(f"Inliers Y-span: {min_y} to {max_y} (Span: {span}px out of {h_src}px, {span_fraction:.2%})")
    
    # Draw third lines
    third_h = h_src / 3.0
    ax.axhline(third_h, color='y', linestyle='--')
    ax.axhline(2 * third_h, color='y', linestyle='--')
    
    fig.savefig(str(FIGURES_DIR / "diagnostic_inlier_locations.png"))
    plt.close(fig)
    
    # 2. Compute per-region RMSE
    print("\n--- Per-Region RMSE ---")
    rmse_global, _ = calculate_rmse(mkpts_ref_c, mkpts_src_c, H)
    print(f"Global RMSE: {rmse_global:.4f}")
    
    for i in range(3):
        y_start = i * third_h
        y_end = (i + 1) * third_h
        
        # Find points in this third
        indices = np.where((mkpts_src_c[:, 1] >= y_start) & (mkpts_src_c[:, 1] < y_end))[0]
        if len(indices) == 0:
            print(f"Third {i+1} ({y_start:.0f}-{y_end:.0f}): 0 inliers, RMSE: N/A")
            continue
            
        pts_src_third = mkpts_src_c[indices]
        pts_ref_third = mkpts_ref_c[indices]
        
        rmse_third, _ = calculate_rmse(pts_ref_third, pts_src_third, H)
        print(f"Third {i+1} ({y_start:.0f}-{y_end:.0f}): {len(indices)} inliers, RMSE: {rmse_third:.4f}")

if __name__ == '__main__':
    main()
