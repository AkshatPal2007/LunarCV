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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import (
    OHRC_IMG_PATH,
    OHRC_SHAPE,
    OHRC_DTYPE,
    OHRC_GSD,
    LRO_IMG_PATH,
    LRO_GSD,
    SCALE_X_LRO_TO_OHRC,
    SCALE_Y_LRO_TO_OHRC,
    FIGURES_DIR,
    OHRC_PROCESSED_DIR,
    LRO_PROCESSED_DIR,
    MATCHES_PROCESSED_DIR,
)
from io_utils import load_ohrc_memmap, load_lro_nac_memmap, extract_patch, print_patch_stats
from outlier_rejection import magsac_filter, print_match_stats
from matching_lightglue import LightGlueFeatureMatcher


def percentile_stretch_uint8(img: np.ndarray, p_low: float = 1.0, p_high: float = 99.0) -> np.ndarray:
    """Minimal normalization: robust percentile stretch to uint8 [0, 255]."""
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    stretched = np.clip((img.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255)
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


def main() -> None:
    print("=" * 70)
    print("LunarCV — Baseline Registration: CH2 OHRC <-> NASA LRO NAC (M1350459544RE)")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Geographic Prior & Memory Mapping
    # ------------------------------------------------------------------
    print(f"\n[1/5] Loading datasets via zero-copy memory mapping...")
    ohrc_mm = load_ohrc_memmap(OHRC_IMG_PATH, shape=OHRC_SHAPE, dtype=OHRC_DTYPE)
    lro_mm, lro_meta = load_lro_nac_memmap(LRO_IMG_PATH)

    print(f"  OHRC shape    : {ohrc_mm.shape} @ {OHRC_GSD} m/px")
    print(f"  LRO NAC shape : {lro_mm.shape} @ {LRO_GSD} m/px")
    print(f"  Anamorphic Scale: X={SCALE_X_LRO_TO_OHRC:.2f}x, Y={SCALE_Y_LRO_TO_OHRC:.2f}x")

    # ------------------------------------------------------------------
    # 2. Extract Overlapping Test Patch
    # ------------------------------------------------------------------
    # In OHRC: scan rows 30,000 - 45,000 (~3.9 km terrain along-track), columns 2,000 - 8,000 (~1.5 km cross-track)
    # Corresponding region in LRO NAC:
    # Latitude ~ -13.33° corresponds to LRO NAC lines ~ 5,500 - 8,500, samples ~ 400 - 1,800
    print(f"\n[2/5] Extracting overlapping target region...")
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
    print(f"\n[3/5] Applying minimal percentile stretch & scale alignment...")
    ohrc_norm = percentile_stretch_uint8(ohrc_raw, p_low=1.0, p_high=99.0)
    lro_norm  = percentile_stretch_uint8(lro_raw, p_low=1.0, p_high=99.0)

    # Anamorphic scale OHRC to match LRO's 2x cross-track binning
    target_w = int(round(ohrc_norm.shape[1] / SCALE_X_LRO_TO_OHRC))
    target_h = int(round(ohrc_norm.shape[0] / SCALE_Y_LRO_TO_OHRC))
    ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)

    print(f"  OHRC scaled to LRO: {ohrc_norm.shape} -> {ohrc_scaled.shape}")
    print(f"  LRO reference patch   : {lro_norm.shape}")

    # ------------------------------------------------------------------
    # 4. Feature Matching (Chunked SuperPoint+LightGlue)
    # ------------------------------------------------------------------
    print(f"\n[4/5] Running SuperPoint+LightGlue feature matching in overlapping chunks...")
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
        
        print(f"  Chunk {i+1}/{n_chunks}: OHRC [{y1_src}:{y2_src}], LRO [{y1_ref}:{y2_ref}]")
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

    print_match_stats(mkpts_src, mkpts_ref, conf, label="SuperPoint+LightGlue (All Chunks)")

    # ------------------------------------------------------------------
    # 5. MAGSAC++ Outlier Rejection & Evaluation
    # ------------------------------------------------------------------
    print(f"\n[5/5] Running MAGSAC++ outlier rejection...")
    mkpts_src_clean, mkpts_ref_clean, conf_clean, H, mask = magsac_filter(
        mkpts_src,
        mkpts_ref,
        conf,
        model="homography",
        ransac_reproj_threshold=4.0,
    )
    print_match_stats(mkpts_src_clean, mkpts_ref_clean, conf_clean, label="Inliers after MAGSAC++")

    # Compute Reprojection RMSE
    if H is not None and len(mkpts_src_clean) >= 4:
        ref_3d = mkpts_ref_clean.astype(np.float32).reshape(-1, 1, 2)
        pred_src = cv2.perspectiveTransform(ref_3d, H).reshape(-1, 2)
        residuals = np.linalg.norm(mkpts_src_clean - pred_src, axis=1)

        rmse = float(np.sqrt(np.mean(residuals**2)))
        median_err = float(np.median(residuals))
        max_err = float(np.max(residuals))
        inlier_ratio = len(mkpts_src_clean) / len(conf) if len(conf) > 0 else 0.0

        print("\n" + "=" * 70)
        print("BASELINE REGISTRATION RESULTS (OHRC <-> LRO NAC)")
        print("=" * 70)
        print(f"  Candidate matches  : {len(conf)}")
        print(f"  Inlier matches     : {len(mkpts_src_clean)}")
        print(f"  Inlier ratio       : {inlier_ratio:.3f}")
        print(f"  Reprojection RMSE  : {rmse:.4f} pixels (Paper SuperGlue Baseline: ~0.60 px)")
        print(f"  Median error       : {median_err:.4f} pixels")
        print(f"  Maximum error      : {max_err:.4f} pixels")
        print("=" * 70)

        # Save match visualization figure
        fig_matches = FIGURES_DIR / "ohrc_lro_baseline_matches.png"
        draw_connected_matches(
            ohrc_scaled,
            lro_norm,
            mkpts_src_clean,
            mkpts_ref_clean,
            fig_matches,
            title=f"OHRC <-> LRO NAC Baseline Matches ({len(mkpts_src_clean)} Inliers, RMSE={rmse:.2f} px)",
        )

        # Save inliers array
        np.save(MATCHES_PROCESSED_DIR / "ohrc_lro_mkpts_src.npy", mkpts_src_clean)
        np.save(MATCHES_PROCESSED_DIR / "ohrc_lro_mkpts_ref.npy", mkpts_ref_clean)
        np.save(MATCHES_PROCESSED_DIR / "ohrc_lro_H.npy", H)
        print(f"  [npy] Saved match arrays to {MATCHES_PROCESSED_DIR}")
    else:
        print("\n❌ Insufficient inliers found to fit homography.")


if __name__ == "__main__":
    main()
