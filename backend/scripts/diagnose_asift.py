import sys
from pathlib import Path
import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lunarcv.config import (
    OHRC_IMG_PATH, OHRC_SHAPE, OHRC_DTYPE,
    LRO_IMG_PATH, LRO_SHAPE, LRO_DTYPE
)
from lunarcv.io.raster import load_ohrc_memmap, load_lro_nac_memmap, extract_patch
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.registration.outlier_rejection import magsac_filter

def percentile_stretch_uint8(img: np.ndarray, p_low: float = 1.0, p_high: float = 99.0) -> np.ndarray:
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    stretched = np.clip((img.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255)
    return stretched.astype(np.uint8)

def main():
    print("--- Stage 1: Coarse Affine via Affine-Simulated LightGlue (ASIFT-style) ---")
    ohrc_mm = load_ohrc_memmap(OHRC_IMG_PATH, shape=OHRC_SHAPE, dtype=OHRC_DTYPE)
    lro_mm, _ = load_lro_nac_memmap(LRO_IMG_PATH)
    
    ohrc_rows = (30000, 45000)
    ohrc_cols = (2000, 8000)
    lro_rows = (5500, 8500)
    lro_cols = (400, 1800)
    
    ohrc_raw = extract_patch(ohrc_mm, ohrc_rows, ohrc_cols)
    lro_raw = extract_patch(lro_mm, lro_rows, lro_cols)
    
    ohrc_norm = percentile_stretch_uint8(ohrc_raw)
    lro_norm = percentile_stretch_uint8(lro_raw)
    
    matcher = LightGlueFeatureMatcher(max_dim=1500, max_keypoints=2048)
    
    # Simulate a range of Y-scales and X-scales around the empirical ones
    base_sy = 4.55
    base_sx = 10.5
    
    # Affine tilts (we will vary sy and sx by +/- 15%)
    scales = [
        (base_sy, base_sx),
        (base_sy * 1.15, base_sx),
        (base_sy * 0.85, base_sx),
        (base_sy, base_sx * 1.15),
        (base_sy, base_sx * 0.85),
        (base_sy * 1.15, base_sx * 1.15),
        (base_sy * 0.85, base_sx * 0.85),
    ]
    
    all_pts_src = []
    all_pts_ref = []
    all_conf = []
    
    # We will do chunking as before, but for each affine simulation
    for sy, sx in scales:
        target_w = int(round(ohrc_norm.shape[1] / sx))
        target_h = int(round(ohrc_norm.shape[0] / sy))
        ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)
        
        n_chunks = 3
        overlap = 400
        h_src, w_src = ohrc_scaled.shape
        h_ref, w_ref = lro_norm.shape
        step_src = (h_src - overlap) // n_chunks
        step_ref = (h_ref - overlap) // n_chunks
        
        for i in range(n_chunks):
            y1_src = i * step_src
            y2_src = y1_src + step_src + overlap if i < n_chunks - 1 else h_src
            y1_ref = i * step_ref
            y2_ref = y1_ref + step_ref + overlap if i < n_chunks - 1 else h_ref
            
            patch_src = ohrc_scaled[y1_src:y2_src, :]
            patch_ref = lro_norm[y1_ref:y2_ref, :]
            
            pts_src, pts_ref, conf = matcher.match(patch_src, patch_ref, conf_threshold=0.0)
            
            if len(pts_src) > 0:
                # Map back to scaled coordinates
                pts_src[:, 1] += y1_src
                pts_ref[:, 1] += y1_ref
                
                # Map back to ORIGINAL OHRC coordinates!
                pts_src_orig = pts_src.copy()
                pts_src_orig[:, 0] *= sx
                pts_src_orig[:, 1] *= sy
                
                all_pts_src.append(pts_src_orig)
                all_pts_ref.append(pts_ref)
                all_conf.append(conf)

    if not all_pts_src:
        print("No matches found across any simulation.")
        return
        
    pts_src = np.vstack(all_pts_src)
    pts_ref = np.vstack(all_pts_ref)
    conf = np.concatenate(all_conf)
    
    print(f"Pooled Raw matches across {len(scales)} simulations: {len(pts_src)}")
    
    # Fit COARSE AFFINE using cv2.estimateAffine2D directly
    H_affine_2x3, raw_mask = cv2.estimateAffine2D(
        pts_src, pts_ref, method=cv2.RANSAC, ransacReprojThreshold=15.0
    )
    
    if H_affine_2x3 is None:
        print("Failed to fit coarse affine.")
        return
        
    mask = raw_mask.ravel().astype(bool)
    mkpts_src_c = pts_src[mask]
    mkpts_ref_c = pts_ref[mask]
    
    print(f"RANSAC Coarse Affine inliers: {len(mkpts_src_c)}")
    
    H_affine = np.vstack([H_affine_2x3, [0, 0, 1]])
    print("Coarse Affine Matrix (OHRC original -> LRO crop):")
    print(H_affine)
    
    # Save the affine for Stage 2
    np.save("coarse_affine.npy", H_affine)
    print("Saved coarse_affine.npy for Stage 2.")
    
    h_src, w_src = ohrc_norm.shape
    min_y = np.min(mkpts_src_c[:, 1])
    max_y = np.max(mkpts_src_c[:, 1])
    span = max_y - min_y
    print(f"Inliers Y-span (Original OHRC): {min_y:.1f} to {max_y:.1f} (Span: {span:.1f}px out of {h_src}px, {span/h_src:.2%})")

if __name__ == "__main__":
    main()
