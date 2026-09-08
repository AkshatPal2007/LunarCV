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
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.matching.rift2_matcher import RIFT2Matcher
from lunarcv.registration.outlier_rejection import magsac_filter

def percentile_stretch_uint8(img: np.ndarray, p_low: float = 1.0, p_high: float = 99.0) -> np.ndarray:
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    stretched = np.clip((img.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255)
    return stretched.astype(np.uint8)

def main():
    print("--- Stage 2: Fine Matching on ASIFT-Corrected Geometry ---")
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
    
    # Load Stage 1 Coarse Affine
    try:
        H_affine = np.load("coarse_affine.npy")
    except FileNotFoundError:
        print("coarse_affine.npy not found! Run Stage 1 first.")
        return
        
    print("Loaded Coarse Affine Matrix:")
    print(H_affine)
    
    # Warp OHRC to perfectly match LRO crop space
    h_ref, w_ref = lro_norm.shape
    ohrc_warped = cv2.warpAffine(ohrc_norm, H_affine[:2, :], (w_ref, h_ref), flags=cv2.INTER_CUBIC)
    
    cv2.imwrite("/home/akshat/Projects/LunarCV/outputs/figures/ohrc_stage2_warped.png", ohrc_warped)
    cv2.imwrite("/home/akshat/Projects/LunarCV/outputs/figures/lro_stage2.png", lro_norm)
    
    matcher = EnsembleMatcher([
        LightGlueFeatureMatcher(max_dim=1500, max_keypoints=2048),
        RIFT2Matcher()
    ])
    
    n_chunks = 3
    overlap = 400
    step_ref = (h_ref - overlap) // n_chunks
    
    all_pts_src = []
    all_pts_ref = []
    all_conf = []
    
    for i in range(n_chunks):
        y1 = i * step_ref
        y2 = y1 + step_ref + overlap if i < n_chunks - 1 else h_ref
        
        patch_src = ohrc_warped[y1:y2, :]
        patch_ref = lro_norm[y1:y2, :]
        
        # Check if patch is mostly black (invalid warp area)
        if np.count_nonzero(patch_src) < 0.1 * patch_src.size:
            continue
            
        pts_src, pts_ref, conf = matcher.match(patch_src, patch_ref, conf_threshold=0.0)
        
        if len(pts_src) > 0:
            pts_src[:, 1] += y1
            pts_ref[:, 1] += y1
            
            # Note: pts_src is in WARPED OHRC space (which is LRO space).
            # To get back to original OHRC space for the final homography/affine,
            # we must invert H_affine.
            
            # Map pts_src back to original OHRC coordinates
            pts_src_hom = np.hstack([pts_src, np.ones((len(pts_src), 1))])
            H_inv = np.linalg.inv(H_affine)
            pts_src_orig = (H_inv @ pts_src_hom.T).T[:, :2]
            
            all_pts_src.append(pts_src_orig)
            all_pts_ref.append(pts_ref)
            all_conf.append(conf)
            
    if not all_pts_src:
        print("No matches found in Stage 2.")
        return
        
    pts_src = np.vstack(all_pts_src)
    pts_ref = np.vstack(all_pts_ref)
    conf = np.concatenate(all_conf)
    
    print(f"--- Fine Matching Complete ---")
    print(f"Raw matches: {len(pts_src)}")
    
    mkpts_src_c, mkpts_ref_c, conf_c, H, mask = magsac_filter(
        pts_src, pts_ref, conf, model="homography", ransac_reproj_threshold=4.0
    )
    
    print(f"MAGSAC++ inliers: {len(mkpts_src_c)}")
    
    if len(mkpts_src_c) > 0:
        h_src, w_src = ohrc_norm.shape
        min_y = np.min(mkpts_src_c[:, 1])
        max_y = np.max(mkpts_src_c[:, 1])
        span = max_y - min_y
        print(f"Inliers Y-span (Original OHRC): {min_y:.1f} to {max_y:.1f} (Span: {span:.1f}px out of {h_src}px, {span/h_src:.2%})")

        from lunarcv.registration.spatial_uniformity import spatial_topk_filter
        mkpts_src_k, _, _ = spatial_topk_filter(
            mkpts_src_c, mkpts_ref_c, conf_c,
            h_src, w_src, n_rows=4, n_cols=4, top_k_per_cell=10
        )
        print(f"After spatial_topk_filter: {len(mkpts_src_k)} inliers distributed across grid.")

if __name__ == "__main__":
    main()
