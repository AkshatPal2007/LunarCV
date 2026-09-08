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
from lunarcv.matching.ensemble import EnsembleMatcher
from lunarcv.registration.outlier_rejection import magsac_filter

def percentile_stretch_uint8(img: np.ndarray, p_low: float = 1.0, p_high: float = 99.0) -> np.ndarray:
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    stretched = np.clip((img.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255)
    return stretched.astype(np.uint8)

def main():
    print("--- Stage 2: Fine Matching on Corrected Geometry (Theoretical GSD) ---")
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
    
    # Theoretical GSD Scales
    scale_y = 1.66 / 0.26 # 6.3846
    scale_x = (1.55 * 2) / 0.26 # 11.9231
    
    target_w = int(round(ohrc_norm.shape[1] / scale_x))
    target_h = int(round(ohrc_norm.shape[0] / scale_y))
    
    print(f"Applying coarse geometric correction: OHRC {ohrc_norm.shape} -> {target_h}x{target_w}")
    ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)
    
    # NO CHUNKING! Let LightGlue resize the whole image to max_dim=2000 so they align globally.
    from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
    from lunarcv.matching.rift2_matcher import RIFT2Matcher
    
    matcher = EnsembleMatcher([
        LightGlueFeatureMatcher(max_dim=2000, max_keypoints=4096),
        RIFT2Matcher()
    ])
    
    pts_src, pts_ref, conf = matcher.match(ohrc_scaled, lro_norm, conf_threshold=0.0)
    
    print(f"Raw matches (Ensemble): {len(pts_src)}")
    if len(pts_src) == 0:
        return
        
    mkpts_src_c, mkpts_ref_c, conf_c, H, mask = magsac_filter(
        pts_src, pts_ref, conf, model="homography", ransac_reproj_threshold=4.0
    )
    
    print(f"MAGSAC++ inliers: {len(mkpts_src_c)}")
    
    if len(mkpts_src_c) > 0:
        h_src, w_src = ohrc_scaled.shape
        min_y = np.min(mkpts_src_c[:, 1])
        max_y = np.max(mkpts_src_c[:, 1])
        span = max_y - min_y
        print(f"Inliers Y-span: {min_y:.1f} to {max_y:.1f} (Span: {span:.1f}px out of {h_src}px, {span/h_src:.2%})")

        from lunarcv.registration.spatial_uniformity import spatial_topk_filter
        mkpts_src_k, _, _ = spatial_topk_filter(
            mkpts_src_c, mkpts_ref_c, conf_c,
            h_src, w_src, n_rows=4, n_cols=4, top_k_per_cell=10
        )
        print(f"After spatial_topk_filter: {len(mkpts_src_k)} inliers distributed across grid.")

if __name__ == "__main__":
    main()
