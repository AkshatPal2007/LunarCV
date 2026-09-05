"""
main_baseline_ohrc_lro.py — Baseline registration pipeline for Chandrayaan-2 OHRC <-> LRO NAC M1350459544RE.

Implements the evidence-updated architecture from CLAUDE.md:
    1. Metadata & Coarse Geographic Prior (OHRC 0.26 m/px, LRO 1.60 m/px -> scale ratio 6.15x)
    2. Minimal normalization (percentile stretch to uint8; no heavy CLAHE by default)
    3. Scale-matched feature matching (LoFTR / LightGlue)
    4. MAGSAC++ outlier rejection (cv2.USAC_MAGSAC)
    5. Evaluation: RMSE, inlier ratio, match count, spatial distribution
    6. Visual overlay validation (side-by-side matches & warped overlay)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lunarcv.config import (
    FIGURES_DIR,
    LRO_GSD,
    LRO_IMG_PATH,
    MATCHES_PROCESSED_DIR,
    OHRC_DTYPE,
    OHRC_GSD,
    OHRC_IMG_PATH,
    OHRC_SHAPE,
    SCALE_X_LRO_TO_OHRC,
    SCALE_Y_LRO_TO_OHRC,
    SUBMISSION_DIR,
)
from lunarcv.io.raster import (
    extract_patch,
    load_lro_nac_memmap,
    load_ohrc_memmap,
    print_patch_stats,
)
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.registration.outlier_rejection import magsac_filter, print_match_stats
from lunarcv.registration.spatial_uniformity import spatial_uniformity_report
from lunarcv.registration.subpixel import refine_matches
from lunarcv.registration.transform import (
    compute_registration,
    make_checkerboard,
    make_overlay,
)


def percentile_stretch_uint8(
    img: np.ndarray, p_low: float = 1.0, p_high: float = 99.0
) -> np.ndarray:
    """Minimal normalization: robust percentile stretch to uint8 [0, 255]."""
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    stretched = np.clip(
        (img.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255
    )
    return stretched.astype(np.uint8)


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
    canvas[:h_ref, w_src : w_src + w_ref] = img_ref

    ax.imshow(canvas, cmap="gray")
    ax.set_title(title, fontsize=13, fontweight="bold")

    colors = plt.cm.rainbow(np.linspace(0, 1, max(1, len(pts_src))))
    for i, (p_src, p_ref) in enumerate(zip(pts_src, pts_ref, strict=True)):
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


def main() -> None:
    print("=" * 70)
    print("LunarCV — Baseline Registration: CH2 OHRC <-> NASA LRO NAC (M1350459544RE)")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Geographic Prior & Memory Mapping
    # ------------------------------------------------------------------
    print("\n[1/5] Loading datasets via zero-copy memory mapping...")
    ohrc_mm = load_ohrc_memmap(OHRC_IMG_PATH, shape=OHRC_SHAPE, dtype=OHRC_DTYPE)
    lro_mm, lro_meta = load_lro_nac_memmap(LRO_IMG_PATH)

    print(f"  OHRC shape    : {ohrc_mm.shape} @ {OHRC_GSD} m/px")
    print(f"  LRO NAC shape : {lro_mm.shape} @ {LRO_GSD} m/px")
    print(
        f"  Anamorphic Scale: X={SCALE_X_LRO_TO_OHRC:.2f}x, Y={SCALE_Y_LRO_TO_OHRC:.2f}x"
    )

    # ------------------------------------------------------------------
    # 2. Extract Overlapping Test Patch
    # ------------------------------------------------------------------
    # In OHRC: scan rows 30,000 - 45,000 (~3.9 km terrain along-track), columns 2,000 - 8,000 (~1.5 km cross-track)
    # Corresponding region in LRO NAC:
    # Latitude ~ -13.33° corresponds to LRO NAC lines ~ 5,500 - 8,500, samples ~ 400 - 1,800
    print("\n[2/5] Extracting overlapping target region...")
    ohrc_rows = (30000, 45000)
    ohrc_cols = (2000, 8000)
    ohrc_raw = extract_patch(ohrc_mm, ohrc_rows, ohrc_cols)
    print_patch_stats(ohrc_raw, label="OHRC raw patch")

    # LRO NAC corresponding lines:
    lro_rows = (5500, 8500)
    lro_cols = (400, 1800)
    lro_raw = extract_patch(lro_mm, lro_rows, lro_cols)
    print_patch_stats(lro_raw, label="LRO NAC raw patch")

    # ------------------------------------------------------------------
    # 3. Minimal Normalization & Scale Alignment
    # ------------------------------------------------------------------
    # Per CLAUDE.md: Minimal normalization (percentile stretch to uint8; NO heavy CLAHE)
    print("\n[3/5] Applying minimal percentile stretch & scale alignment...")
    ohrc_norm = percentile_stretch_uint8(ohrc_raw, p_low=1.0, p_high=99.0)
    lro_norm = percentile_stretch_uint8(lro_raw, p_low=1.0, p_high=99.0)

    # Anamorphic scale OHRC to match LRO's 2x cross-track binning
    target_w = int(round(ohrc_norm.shape[1] / SCALE_X_LRO_TO_OHRC))
    target_h = int(round(ohrc_norm.shape[0] / SCALE_Y_LRO_TO_OHRC))
    ohrc_scaled = cv2.resize(
        ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA
    )

    print(f"  OHRC scaled to LRO: {ohrc_norm.shape} -> {ohrc_scaled.shape}")
    print(f"  LRO reference patch   : {lro_norm.shape}")

    # ------------------------------------------------------------------
    # 4. Feature Matching (Chunked SuperPoint+LightGlue)
    # ------------------------------------------------------------------
    print(
        "\n[4/5] Running SuperPoint+LightGlue feature matching in overlapping chunks..."
    )
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

        print(
            f"  Chunk {i + 1}/{n_chunks}: OHRC [{y1_src}:{y2_src}], LRO [{y1_ref}:{y2_ref}]"
        )
        pts_src, pts_ref, conf = matcher.match(patch_src, patch_ref, conf_threshold=0.0)

        if len(pts_src) > 0:
            pts_src[:, 1] += y1_src
            pts_ref[:, 1] += y1_ref
            all_mkpts_src.append(pts_src)
            all_mkpts_ref.append(pts_ref)
            all_conf.append(conf)

    if len(all_mkpts_src) > 0:
        mkpts_src = np.vstack(all_mkpts_src)
        mkpts_ref = np.vstack(all_mkpts_ref)
        conf = np.concatenate(all_conf)
    else:
        mkpts_src = np.empty((0, 2), dtype=np.float32)
        mkpts_ref = np.empty((0, 2), dtype=np.float32)
        conf = np.empty((0,), dtype=np.float32)

    print_match_stats(
        mkpts_src, mkpts_ref, conf, label="SuperPoint+LightGlue (All Chunks)"
    )

    # ------------------------------------------------------------------
    # 5. MAGSAC++ Outlier Rejection & Evaluation
    # ------------------------------------------------------------------
    print("\n[5/5] Running MAGSAC++ outlier rejection...")
    mkpts_src_clean, mkpts_ref_clean, conf_clean, H, mask = magsac_filter(
        mkpts_src,
        mkpts_ref,
        conf,
        model="homography",
        ransac_reproj_threshold=4.0,
    )
    print_match_stats(
        mkpts_src_clean, mkpts_ref_clean, conf_clean, label="Inliers after MAGSAC++"
    )

    if H is None or len(mkpts_src_clean) < 4:
        print("\n❌ Insufficient inliers found to fit homography.")
        return

    # Spatial uniformity — report on MAGSAC++ inliers (our differentiator vs. the paper)
    h_src, w_src = ohrc_scaled.shape
    spatial_uniformity_report(
        mkpts_src_clean, h_src, w_src, label="MAGSAC++ inliers", n_rows=4, n_cols=4
    )

    # ------------------------------------------------------------------
    # 6. Sub-Pixel Refinement & Final Homography
    # ------------------------------------------------------------------
    print("\n[6/6] Running Sub-Pixel Refinement (win_size=2)...")
    mkpts_src_ref, mkpts_ref_ref, stats = refine_matches(
        ohrc_scaled,
        lro_norm,
        mkpts_src_clean,
        mkpts_ref_clean,
        win_size=(2, 2),
        zero_zone=(-1, -1),
        min_eigen_threshold=1e-5,
    )

    print(
        f"  Successfully refined: {stats['successfully_refined']} / {stats['total_points']}"
    )
    print(f"  Mean displacement   : {stats['mean_displacement']:.4f} pixels")

    # Spatial uniformity — report on final sub-pixel refined points
    su_final = spatial_uniformity_report(
        mkpts_src_ref,
        h_src,
        w_src,
        label="Sub-pixel refined inliers",
        n_rows=4,
        n_cols=4,
    )

    # Re-estimate final homography + warp via transform.py
    reg = compute_registration(
        ref_img=lro_norm,
        src_img=ohrc_scaled,
        pts_ref=mkpts_ref_ref,
        pts_src=mkpts_src_ref,
    )

    if reg is None:
        print("\n❌ Failed to fit final homography after refinement.")
        return

    H_final = reg.H

    # Compute reprojection RMSE
    ref_3d = mkpts_ref_ref.astype(np.float32).reshape(-1, 1, 2)
    pred_src = cv2.perspectiveTransform(ref_3d, H_final).reshape(-1, 2)
    residuals = np.linalg.norm(mkpts_src_ref - pred_src, axis=1)

    rmse = float(np.sqrt(np.mean(residuals**2)))
    median_err = float(np.median(residuals))
    max_err = float(np.max(residuals))
    inlier_ratio = len(mkpts_src_ref) / len(conf) if len(conf) > 0 else 0.0

    print("\n" + "=" * 70)
    print("FINAL REGISTRATION RESULTS (OHRC <-> LRO NAC)")
    print("=" * 70)
    print(f"  Candidate matches  : {len(conf)}")
    print(f"  Inlier matches     : {len(mkpts_src_ref)}")
    print(f"  Inlier ratio       : {inlier_ratio:.3f}")
    print(f"  Reprojection RMSE  : {rmse:.4f} pixels (Sub-pixel refined)")
    print(f"  Median error       : {median_err:.4f} pixels")
    print(f"  Maximum error      : {max_err:.4f} pixels")
    print("=" * 70)

    # Save match visualisation figure
    draw_connected_matches(
        ohrc_scaled,
        lro_norm,
        mkpts_src_ref,
        mkpts_ref_ref,
        FIGURES_DIR / "ohrc_lro_baseline_matches_refined.png",
        title=f"OHRC <-> LRO NAC Refined Matches ({len(mkpts_src_ref)} Inliers, RMSE={rmse:.2f} px)",
    )

    # Save refined arrays
    np.save(MATCHES_PROCESSED_DIR / "ohrc_lro_mkpts_src.npy", mkpts_src_ref)
    np.save(MATCHES_PROCESSED_DIR / "ohrc_lro_mkpts_ref.npy", mkpts_ref_ref)
    np.save(MATCHES_PROCESSED_DIR / "ohrc_lro_H.npy", H_final)
    print(f"  [npy] Saved refined match arrays to {MATCHES_PROCESSED_DIR}")

    # ------------------------------------------------------------------
    # 7. Generate Final Hackathon Submission Products
    # ------------------------------------------------------------------
    print("\n[7/7] Generating submission products...")

    x_min, y_min, x_max, y_max = reg.bbox
    out_h, out_w = reg.canvas_shape
    print(f"  [diag] Original LRO size      : {lro_norm.shape}")
    print(f"  [diag] Transformed LRO corners:\n{reg.warped_corners}")
    print(
        f"  [diag] Bounding Box           : x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]"
    )
    print(f"  [diag] Output canvas size     : ({out_h}, {out_w})")
    print(
        f"  [diag] Valid overlap area     : {reg.mask_overlap.sum()} px ({reg.overlap_pct:.1f}% of warped LRO)"
    )

    # 1. Registered image, overlay, checkerboard
    cv2.imwrite(str(SUBMISSION_DIR / "registered.png"), reg.warped_ref)

    overlay, _ = make_overlay(
        reg.warped_ref, reg.warped_src, reg.mask_ref, reg.mask_src
    )
    cv2.imwrite(str(SUBMISSION_DIR / "overlay.png"), overlay)

    checker = make_checkerboard(
        reg.warped_ref,
        reg.warped_src,
        reg.mask_ref,
        reg.mask_src,
        reg.mask_overlap,
        grid_size=50,
    )
    cv2.imwrite(str(SUBMISSION_DIR / "checkerboard.png"), checker)

    # 1d. Diagnostic figure
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes[0, 0].imshow(ohrc_scaled, cmap="gray")
    axes[0, 0].set_title("Original OHRC")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(lro_norm, cmap="gray")
    axes[0, 1].set_title("Original LRO NAC")
    axes[0, 1].axis("off")

    axes[0, 2].imshow(reg.warped_ref, cmap="gray")
    axes[0, 2].set_title("Warped LRO")
    axes[0, 2].axis("off")

    axes[1, 0].imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title("Alpha Overlay")
    axes[1, 0].axis("off")

    axes[1, 1].imshow(checker, cmap="gray")
    axes[1, 1].set_title("Checkerboard")
    axes[1, 1].axis("off")
    axes[1, 2].axis("off")

    fig.tight_layout()
    fig.savefig(
        FIGURES_DIR / "registration_product_diagnostic.png",
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)

    print(
        f"  [out] Saved registered.png, overlay.png, checkerboard.png -> {SUBMISSION_DIR}"
    )
    print(
        f"  [out] Saved diagnostic plot -> {FIGURES_DIR / 'registration_product_diagnostic.png'}"
    )

    # 2. Correspondence CSV
    csv_path = SUBMISSION_DIR / "correspondence_points.csv"
    with open(csv_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source_x", "source_y", "reference_x", "reference_y"])
        for pt_s, pt_r in zip(mkpts_src_ref, mkpts_ref_ref, strict=True):
            writer.writerow([pt_s[0], pt_s[1], pt_r[0], pt_r[1]])
    print(f"  [out] Saved correspondence CSV -> {csv_path}")

    # 3. Metrics JSON (spatial uniformity is our differentiator vs the paper)
    metrics = {
        "candidate_matches": len(conf),
        "inlier_matches": len(mkpts_src_ref),
        "inlier_ratio": inlier_ratio,
        "reprojection_rmse_px": rmse,
        "median_error_px": median_err,
        "max_error_px": max_err,
        "mean_displacement_px": stats["mean_displacement"],
        "spatial_uniformity": {
            "grid_occupancy_pct": su_final["occupancy_pct"],
            "convex_hull_coverage_pct": su_final["hull_coverage_pct"],
            "min_point_separation_px": su_final["min_separation_px"],
        },
    }
    json_path = SUBMISSION_DIR / "metrics.json"
    with open(json_path, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"  [out] Saved evaluation metrics -> {json_path}")


if __name__ == "__main__":
    main()
