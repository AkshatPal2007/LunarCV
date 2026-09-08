import sys
from pathlib import Path
import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lunarcv.config import (
    OHRC_IMG_PATH, OHRC_SHAPE, OHRC_DTYPE,
    LRO_IMG_PATH, LRO_SHAPE, LRO_DTYPE,
    SCALE_X_LRO_TO_OHRC, SCALE_Y_LRO_TO_OHRC
)
from lunarcv.io.raster import load_ohrc_memmap, load_lro_nac_memmap, extract_patch
from lunarcv.matching.ensemble import EnsembleMatcher
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.matching.rift2_matcher import RIFT2Matcher

def percentile_stretch_uint8(img: np.ndarray, p_low: float = 1.0, p_high: float = 99.0) -> np.ndarray:
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    stretched = np.clip((img.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255)
    return stretched.astype(np.uint8)

def decompose_affine(M):
    """Decompose 2x3 affine matrix into translation, scale, rotation."""
    a, b, tx = M[0, 0], M[0, 1], M[0, 2]
    c, d, ty = M[1, 0], M[1, 1], M[1, 2]
    
    det = a * d - b * c
    sx = np.sqrt(a**2 + c**2)
    sy = np.sqrt(b**2 + d**2)
    # Use det sign for scale_x to handle reflection, though we shouldn't have reflection
    if det < 0:
        sx = -sx
    
    rot_rad = np.arctan2(c, a)
    rot_deg = np.degrees(rot_rad)
    
    return tx, ty, sx, sy, rot_deg, det

def run_chunking_experiment(ohrc_norm, lro_norm, n_chunks, overlap_ratio=0.2):
    print(f"\n{'='*60}")
    print(f"RUNNING CONFIGURATION: {n_chunks} CHUNKS")
    print(f"{'='*60}")
    
    matcher = EnsembleMatcher([
        LightGlueFeatureMatcher(max_dim=1500, max_keypoints=2048),
        RIFT2Matcher()
    ])
    
    # Scale OHRC
    sx = SCALE_X_LRO_TO_OHRC # 10.5
    sy = SCALE_Y_LRO_TO_OHRC # 4.55
    target_w = int(round(ohrc_norm.shape[1] / sx))
    target_h = int(round(ohrc_norm.shape[0] / sy))
    ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)
    
    h_src, w_src = ohrc_scaled.shape
    h_ref, w_ref = lro_norm.shape
    
    # Chunking logic
    overlap_src = int(h_src * overlap_ratio / n_chunks) * 5 # Roughly 20% overlap
    overlap_ref = int(h_ref * overlap_ratio / n_chunks) * 5
    
    step_src = (h_src - overlap_src) // n_chunks
    step_ref = (h_ref - overlap_ref) // n_chunks
    
    results = []
    
    for i in range(n_chunks):
        y1_src = i * step_src
        y2_src = y1_src + step_src + overlap_src if i < n_chunks - 1 else h_src
        y1_ref = i * step_ref
        y2_ref = y1_ref + step_ref + overlap_ref if i < n_chunks - 1 else h_ref
        
        patch_src = ohrc_scaled[y1_src:y2_src, :]
        patch_ref = lro_norm[y1_ref:y2_ref, :]
        
        y_center_orig = (y1_src + (y2_src - y1_src) / 2) * sy
        
        pts_src, pts_ref, conf = matcher.match(patch_src, patch_ref, conf_threshold=0.0)
        
        chunk_res = {
            "chunk_id": i + 1,
            "y_center_orig": y_center_orig,
            "ohrc_bounds": (y1_src, y2_src),
            "lro_bounds": (y1_ref, y2_ref),
            "raw_matches": len(pts_src),
            "status": "REJECTED",
            "reason": "Insufficient matches (< 4)",
            "inliers": 0,
            "inlier_ratio": 0.0,
            "rmse": 0.0,
            "pts_src_orig": None,
            "pts_ref_orig": None,
            "det": 0.0,
            "tx": 0.0, "ty": 0.0, "sx": 0.0, "sy": 0.0, "rot": 0.0
        }
        
        if len(pts_src) >= 4:
            # Map back to SCALED coordinates
            pts_src_scaled = pts_src.copy()
            pts_src_scaled[:, 1] += y1_src
            
            pts_ref_global = pts_ref.copy()
            pts_ref_global[:, 1] += y1_ref
            
            # Map source to ORIGINAL OHRC coordinates
            pts_src_orig = pts_src_scaled.copy()
            pts_src_orig[:, 0] *= sx
            pts_src_orig[:, 1] *= sy
            
            # Fit Affine
            M, raw_mask = cv2.estimateAffine2D(
                pts_src_orig, pts_ref_global, method=cv2.RANSAC, ransacReprojThreshold=15.0
            )
            
            if M is not None:
                mask = raw_mask.ravel().astype(bool)
                n_inliers = mask.sum()
                chunk_res["inliers"] = n_inliers
                chunk_res["inlier_ratio"] = n_inliers / len(pts_src)
                
                tx, ty, scale_x, scale_y, rot, det = decompose_affine(M)
                chunk_res["tx"] = tx
                chunk_res["ty"] = ty
                chunk_res["sx"] = scale_x
                chunk_res["sy"] = scale_y
                chunk_res["rot"] = rot
                chunk_res["det"] = det
                
                # Compute RMSE
                if n_inliers > 0:
                    pts_src_in = pts_src_orig[mask]
                    pts_ref_in = pts_ref_global[mask]
                    
                    pts_src_hom = np.hstack([pts_src_in, np.ones((n_inliers, 1))])
                    pts_proj = (M @ pts_src_hom.T).T
                    err = np.linalg.norm(pts_proj - pts_ref_in, axis=1)
                    chunk_res["rmse"] = np.mean(err)
                    
                    chunk_res["pts_src_orig"] = pts_src_in
                    chunk_res["pts_ref_orig"] = pts_ref_in
                
                # Degeneracy Checks
                if n_inliers < 5:
                    chunk_res["reason"] = "insufficient geometric support"
                elif abs(det) < 0.01:
                    chunk_res["reason"] = "degenerate determinant (near zero)"
                elif scale_x < 0.01 or scale_y < 0.01 or scale_x > 2.0 or scale_y > 2.0:
                    chunk_res["reason"] = f"absurd scale (sx={scale_x:.3f}, sy={scale_y:.3f})"
                elif abs(rot) > 45.0:
                    chunk_res["reason"] = f"extreme rotation ({rot:.1f} deg)"
                elif chunk_res["rmse"] > 10.0:
                    chunk_res["reason"] = f"excessive reprojection error ({chunk_res['rmse']:.1f}px)"
                else:
                    chunk_res["status"] = "ACCEPTED"
                    chunk_res["reason"] = ""
            else:
                chunk_res["reason"] = "RANSAC model estimation failed"
        
        results.append(chunk_res)
        
        print(f"\nChunk {i+1:02d}")
        print(f"OHRC Bounds: {y1_src}:{y2_src} | LRO Bounds: {y1_ref}:{y2_ref}")
        print(f"Raw matches:       {chunk_res['raw_matches']}")
        print(f"RANSAC inliers:    {chunk_res['inliers']}")
        if chunk_res["raw_matches"] > 0:
            print(f"Inlier ratio:      {chunk_res['inlier_ratio']:.1%}")
        print(f"Reprojection RMSE: {chunk_res['rmse']:.2f} px")
        print(f"determinant:       {chunk_res['det']:.4f}")
        print(f"Status:            {chunk_res['status']}")
        if chunk_res["status"] == "REJECTED":
            print(f"Reason:            {chunk_res['reason']}")
            
    # Compile Deduplicated Stats & Coverage
    all_src = []
    all_ref = []
    
    for res in results:
        if res["status"] == "ACCEPTED":
            all_src.append(res["pts_src_orig"])
            all_ref.append(res["pts_ref_orig"])
            
    total_raw = sum(r["raw_matches"] for r in results)
    
    if all_src:
        global_src = np.vstack(all_src)
        global_ref = np.vstack(all_ref)
        
        # Deduplicate matches (quantize coordinates to remove overlap dupes)
        quantized = np.round(global_src).astype(int)
        _, unique_indices = np.unique(quantized, axis=0, return_index=True)
        global_src = global_src[unique_indices]
        global_ref = global_ref[unique_indices]
        
        total_inliers = len(global_src)
        
        # Spatial Coverage on OHRC original crop (15000 x 6000)
        h_orig, w_orig = ohrc_norm.shape
        min_y, max_y = np.min(global_src[:, 1]), np.max(global_src[:, 1])
        min_x, max_x = np.min(global_src[:, 0]), np.max(global_src[:, 0])
        
        box_area = (max_x - min_x) * (max_y - min_y)
        coverage_pct = box_area / (h_orig * w_orig) * 100.0
        
        # Bins 4x4
        bins_y = np.linspace(0, h_orig, 5)
        bins_x = np.linspace(0, w_orig, 5)
        grid_counts, _, _ = np.histogram2d(global_src[:, 1], global_src[:, 0], bins=[bins_y, bins_x])
        occupied_bins = np.count_nonzero(grid_counts)
        
        # Plot Global Scatter
        plt.figure(figsize=(6, 12))
        plt.scatter(global_src[:, 0], global_src[:, 1], c='blue', s=2, alpha=0.5)
        plt.xlim(0, w_orig)
        plt.ylim(h_orig, 0) # Invert Y for image coords
        plt.title(f"Global Inlier Coverage ({n_chunks} chunks)")
        plt.savefig(f"/home/akshat/Projects/LunarCV/outputs/figures/coverage_{n_chunks}chunks.png")
        plt.close()
        
    else:
        total_inliers = 0
        min_x, max_x, min_y, max_y = 0, 0, 0, 0
        coverage_pct = 0.0
        occupied_bins = 0
        
    # Plot Local Transform Variation
    accepted = [r for r in results if r["status"] == "ACCEPTED"]
    if accepted:
        y_centers = [r["y_center_orig"] for r in accepted]
        sxs = [r["sx"] for r in accepted]
        sys = [r["sy"] for r in accepted]
        rots = [r["rot"] for r in accepted]
        
        fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
        axes[0].scatter(y_centers, sxs, color='r')
        axes[0].set_ylabel('Scale X')
        axes[0].set_title(f'Local Transform Variation ({n_chunks} chunks)')
        
        axes[1].scatter(y_centers, sys, color='g')
        axes[1].set_ylabel('Scale Y')
        
        axes[2].scatter(y_centers, rots, color='b')
        axes[2].set_ylabel('Rotation (deg)')
        axes[2].set_xlabel('OHRC Y-Coordinate')
        
        plt.savefig(f"/home/akshat/Projects/LunarCV/outputs/figures/variation_{n_chunks}chunks.png")
        plt.close()
        
    # Medians
    medians = {}
    if accepted:
        medians["raw"] = np.median([r["raw_matches"] for r in accepted])
        medians["inliers"] = np.median([r["inliers"] for r in accepted])
        medians["ratio"] = np.median([r["inlier_ratio"] for r in accepted])
        medians["rmse"] = np.median([r["rmse"] for r in accepted])
        medians["det"] = np.median([r["det"] for r in accepted])
        medians["sx"] = np.median([r["sx"] for r in accepted])
        medians["sy"] = np.median([r["sy"] for r in accepted])
    
    return {
        "n_chunks": n_chunks,
        "total_raw": total_raw,
        "total_inliers": total_inliers,
        "coverage_pct": coverage_pct,
        "occupied_bins": occupied_bins,
        "medians": medians
    }

def main():
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
    
    res_8 = run_chunking_experiment(ohrc_norm, lro_norm, n_chunks=8)
    res_12 = run_chunking_experiment(ohrc_norm, lro_norm, n_chunks=12)
    
    print("\n" + "="*80)
    print("FINAL SUMMARY COMPARISON")
    print("="*80)
    print(f"{'Method':<20} | {'Chunks':>6} | {'Raw Matches':>11} | {'Verified Inliers':>16} | {'Coverage (%)':>12} | {'Grid (16)':>10}")
    print("-" * 80)
    print(f"{'Existing baseline':<20} | {'3':>6} | {'~45':>11} | {'7':>16} | {'~27.0%':>12} | {'4/16':>10}")
    print(f"{'Dense local A':<20} | {res_8['n_chunks']:>6} | {res_8['total_raw']:>11} | {res_8['total_inliers']:>16} | {res_8['coverage_pct']:>11.1f}% | {res_8['occupied_bins']:>4}/16")
    print(f"{'Dense local B':<20} | {res_12['n_chunks']:>6} | {res_12['total_raw']:>11} | {res_12['total_inliers']:>16} | {res_12['coverage_pct']:>11.1f}% | {res_12['occupied_bins']:>4}/16")
    print("="*80)
    
    for cfg, name in [(res_8, "Dense local A"), (res_12, "Dense local B")]:
        if cfg["medians"]:
            print(f"\n{name} Medians (across accepted chunks):")
            print(f"  Raw matches/chunk: {cfg['medians']['raw']:.1f}")
            print(f"  Inliers/chunk:     {cfg['medians']['inliers']:.1f}")
            print(f"  Inlier ratio:      {cfg['medians']['ratio']:.1%}")
            print(f"  RMSE:              {cfg['medians']['rmse']:.2f}")
            print(f"  Determinant:       {cfg['medians']['det']:.4f}")
            print(f"  Scale X:           {cfg['medians']['sx']:.4f}")
            print(f"  Scale Y:           {cfg['medians']['sy']:.4f}")

if __name__ == "__main__":
    main()
