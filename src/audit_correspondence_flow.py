"""
audit_correspondence_flow.py — Deep Trace & Index Audit of the Feature Pipeline.

Traces every correspondence from LoFTR output -> scaling -> MAGSAC++ -> homography -> arrays.
Preserves original match indices at every step to detect indexing, ordering, or scaling bugs.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
import numpy as np

from config import (
    TMC2_IMG_PATH,
    TMC2_SHAPE,
    TMC2_DTYPE,
    LRO_IMG_PATH,
    TMC2_PROCESSED_DIR,
    LRO_PROCESSED_DIR,
)
from io_utils import load_tmc2_memmap, load_lro_nac_memmap, extract_patch
from preprocessing import normalize_uint16_to_uint8, apply_clahe
from matching import LoFTRMatcher


def audit_full_pipeline_flow() -> None:
    print("=" * 70)
    print("DEEP CORRESPONDENCE FLOW & INDEX AUDIT")
    print("=" * 70)

    # 1. Load TMC-2 & LRO arrays
    tmc2_memmap = load_tmc2_memmap(TMC2_IMG_PATH, shape=TMC2_SHAPE, dtype=TMC2_DTYPE)
    tmc2_raw = extract_patch(tmc2_memmap, (50000, 54000), (1000, 3000))
    tmc2_norm = normalize_uint16_to_uint8(tmc2_raw)
    tmc2_clahe = apply_clahe(tmc2_norm)

    lro_memmap, _ = load_lro_nac_memmap(LRO_IMG_PATH)
    lro_full = np.array(lro_memmap)
    lro_down = cv2.resize(
        lro_full,
        (lro_full.shape[1] // 10, lro_full.shape[0] // 10),
        interpolation=cv2.INTER_AREA,
    )
    lro_clahe = apply_clahe(lro_down)

    print(f"Image shapes: TMC-2 {tmc2_clahe.shape}, LRO {lro_clahe.shape}")

    # 2. Run LoFTR and capture un-scaled & scaled points
    matcher = LoFTRMatcher(pretrained="outdoor", max_dim=1024)

    # Manually inspect internal LoFTR scaling logic
    src_proc, scale_src = matcher._resize_for_loftr(tmc2_clahe)
    ref_proc, scale_ref = matcher._resize_for_loftr(lro_clahe)

    print(f"\n[LoFTR Resize Audit]")
    print(f"  TMC-2 original {tmc2_clahe.shape} -> resized {src_proc.shape} | scale_xy = {scale_src}")
    print(f"  LRO   original {lro_clahe.shape} -> resized {ref_proc.shape} | scale_xy = {scale_ref}")

    # Run LoFTR inference
    import torch
    def to_tensor(img: np.ndarray) -> torch.Tensor:
        return (torch.from_numpy(img.astype(np.float32) / 255.0)
                .unsqueeze(0).unsqueeze(0).to(matcher.device))

    batch = {"image0": to_tensor(src_proc), "image1": to_tensor(ref_proc)}
    with torch.no_grad():
        out = matcher.model(batch)

    pts0_raw = out["keypoints0"].cpu().numpy()  # in resized TMC-2 space
    pts1_raw = out["keypoints1"].cpu().numpy()  # in resized LRO space
    conf_raw = out["confidence"].cpu().numpy()

    print(f"\n[LoFTR Raw Output]")
    print(f"  Total raw matches returned: {len(conf_raw)}")

    # Assign original global IDs
    orig_indices = np.arange(len(conf_raw))

    # Apply confidence thresholding
    conf_thresh = 0.35
    conf_mask = conf_raw >= conf_thresh

    indices_cand = orig_indices[conf_mask]
    pts0_cand_res = pts0_raw[conf_mask]
    pts1_cand_res = pts1_raw[conf_mask]
    conf_cand = conf_raw[conf_mask]

    print(f"\n[Confidence Thresholding (conf >= {conf_thresh})]")
    print(f"  Candidates remaining: {len(indices_cand)}")

    # Scale keypoints to original image spaces
    # pts0 is TMC-2 (target), pts1 is LRO (source)
    pts0_cand_orig = pts0_cand_res * scale_src
    pts1_cand_orig = pts1_cand_res * scale_ref

    # 3. Audit MAGSAC++ Execution
    print("\n[MAGSAC++ Execution Audit]")
    # We want Homography mapping LRO (pts1_cand_orig) -> TMC-2 (pts0_cand_orig)
    ransac_thresh = 5.0
    ref_points_for_magsac = pts1_cand_orig.astype(np.float32)
    src_points_for_magsac = pts0_cand_orig.astype(np.float32)

    H_magsac, inlier_mask_raw = cv2.findHomography(
        ref_points_for_magsac,
        src_points_for_magsac,
        method=cv2.USAC_MAGSAC,
        ransacReprojThreshold=ransac_thresh,
        maxIters=10000,
        confidence=0.999,
    )

    if H_magsac is None or inlier_mask_raw is None:
        print("❌ MAGSAC++ failed to find homography.")
        return

    inlier_mask = inlier_mask_raw.ravel().astype(bool)
    n_inliers = inlier_mask.sum()

    print(f"  H_magsac estimated successfully.")
    print(f"  Raw inlier mask sum: {n_inliers} out of {len(inlier_mask)}")

    # 4. Compute Reprojection Residuals for ALL Candidates using H_magsac
    ref_3d = ref_points_for_magsac.reshape(-1, 1, 2)
    pred_src_all = cv2.perspectiveTransform(ref_3d, H_magsac).reshape(-1, 2)
    residuals_all = np.linalg.norm(src_points_for_magsac - pred_src_all, axis=1)

    # 5. Print Detailed Trace Table with Original Indices
    print("\n" + "=" * 90)
    print(f"{'Orig ID':<8} | {'MAGSAC Inlier?':<15} | {'LRO Ref (x,y)':<18} | {'TMC2 Src (x,y)':<18} | {'Pred Src (x,y)':<18} | {'Residual (px)':<12}")
    print("=" * 90)

    inlier_residuals = []
    inlier_pts_src = []
    inlier_pts_ref = []

    for i in range(len(indices_cand)):
        orig_id = indices_cand[i]
        is_inlier = inlier_mask[i]
        ref_x, ref_y = ref_points_for_magsac[i]
        src_x, src_y = src_points_for_magsac[i]
        pred_x, pred_y = pred_src_all[i]
        res = residuals_all[i]

        status_str = "✅ INLIER" if is_inlier else "❌ outlier"
        print(f"{orig_id:<8d} | {status_str:<15} | ({ref_x:6.1f}, {ref_y:6.1f}) | ({src_x:6.1f}, {src_y:6.1f}) | ({pred_x:6.1f}, {pred_y:6.1f}) | {res:10.4f} px")

        if is_inlier:
            inlier_residuals.append(res)
            inlier_pts_src.append([src_x, src_y])
            inlier_pts_ref.append([ref_x, ref_y])

    print("=" * 90)

    inlier_residuals = np.array(inlier_residuals)
    inlier_pts_src = np.array(inlier_pts_src)
    inlier_pts_ref = np.array(inlier_pts_ref)

    # 6. Verify Assertion: Every masked inlier MUST have residual <= threshold
    max_inlier_res = np.max(inlier_residuals) if len(inlier_residuals) > 0 else 0.0
    print(f"\n[MAGSAC Mask Consistency Check]")
    print(f"  Configured Threshold : {ransac_thresh} px")
    print(f"  Max Inlier Residual  : {max_inlier_res:.4f} px")

    if max_inlier_res > ransac_thresh + 1e-3:
        print(f"❌ BUG DETECTED! Inlier mask contains points with residual > threshold!")
    else:
        print(f"✅ PASSED: MAGSAC mask is 100% consistent with H_magsac (all inliers <= {ransac_thresh} px).")

    # 7. Compare with re-estimating H from inliers alone vs H_magsac
    if len(inlier_pts_src) >= 4:
        H_inliers_only, _ = cv2.findHomography(inlier_pts_ref, inlier_pts_src, method=0)
        pred_inliers_only = cv2.perspectiveTransform(inlier_pts_ref.reshape(-1, 1, 2), H_inliers_only).reshape(-1, 2)
        res_inliers_only = np.linalg.norm(inlier_pts_src - pred_inliers_only, axis=1)

        print(f"\n[H Re-estimation Audit (H from 6 inliers alone)]")
        print(f"  Inlier-only H RMSE : {np.sqrt(np.mean(res_inliers_only**2)):.4f} px")
        print(f"  Inlier-only H Max  : {np.max(res_inliers_only):.4f} px")
        for k in range(len(inlier_pts_src)):
            print(f"   Inlier point {k}: residual = {res_inliers_only[k]:.4f} px")

    # 8. Spatial Convex Hull & Dispersion Audit
    if len(inlier_pts_src) >= 3:
        hull_src = cv2.convexHull(inlier_pts_src.astype(np.float32))
        hull_area_src = cv2.contourArea(hull_src)
        patch_area_src = tmc2_clahe.shape[0] * tmc2_clahe.shape[1]
        area_ratio_src = hull_area_src / patch_area_src

        print(f"\n[Convex Hull & Spatial Geometry Audit]")
        print(f"  TMC-2 Inlier Convex Hull Area : {hull_area_src:.1f} sq px ({area_ratio_src*100:.2f}% of patch)")
        print(f"  Geometry Status               : {'⚠️ DEGENERATE / NEARLY COLLINEAR' if area_ratio_src < 0.05 else '✅ WELL DISTRIBUTED'}")


if __name__ == "__main__":
    audit_full_pipeline_flow()
