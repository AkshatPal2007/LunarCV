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
    print("--- Re-running Matcher with Theoretical Scale ---")
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
    
    # Theoretical scales
    scale_y = 1.66 / 0.26 # 6.38
    scale_x = (1.55 * 2) / 0.26 # 11.92
    
    target_w = int(round(ohrc_norm.shape[1] / scale_x))
    target_h = int(round(ohrc_norm.shape[0] / scale_y))
    
    print(f"Resizing OHRC from {ohrc_norm.shape} to {target_h}x{target_w}")
    ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)
    
    matcher = LightGlueFeatureMatcher(max_dim=1500, max_keypoints=2048)
    
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

    if all_mkpts_src:
        mkpts_src = np.vstack(all_mkpts_src)
        mkpts_ref = np.vstack(all_mkpts_ref)
        conf = np.concatenate(all_conf)
        print(f"Raw matches with theoretical scale: {len(mkpts_src)}")
        
        mkpts_src_c, mkpts_ref_c, conf_c, H, mask = magsac_filter(
            mkpts_src, mkpts_ref, conf, model="homography", ransac_reproj_threshold=4.0
        )
        print(f"MAGSAC++ inliers with theoretical scale: {len(mkpts_src_c)}")
        
        # Inliers Y-span
        if len(mkpts_src_c) > 0:
            min_y = np.min(mkpts_src_c[:, 1])
            max_y = np.max(mkpts_src_c[:, 1])
            span = max_y - min_y
            print(f"Inliers Y-span: {min_y:.1f} to {max_y:.1f} (Span: {span:.1f}px out of {h_src}px, {span/h_src:.2%})")
            
            min_y_ref = np.min(mkpts_ref_c[:, 1])
            max_y_ref = np.max(mkpts_ref_c[:, 1])
            span_ref = max_y_ref - min_y_ref
            print(f"Ref Inliers Y-span: {min_y_ref:.1f} to {max_y_ref:.1f} (Span: {span_ref:.1f}px out of {h_ref}px, {span_ref/h_ref:.2%})")
            
            print(f"Ratio of matched spans (Ref / Src): {span_ref / span:.2f}")

    else:
        print("0 matches found!")

if __name__ == "__main__":
    main()
