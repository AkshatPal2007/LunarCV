"""
matcher_benchmark.py

Controlled side-by-side benchmark of LoFTR vs LightGlue (ALIKED).
Identical pipeline for both: same crop, scale, normalization,
spatial uniformity, MAGSAC++, and evaluation.

Usage:
    python src/matcher_benchmark.py

This will:
1. Load cached LoFTR candidates (if available) or run LoFTR
2. Run LightGlue (ALIKED)
3. Evaluate both under identical conditions
4. Save outputs/metrics/matcher_benchmark.csv + .json
5. Save visualizations to outputs/figures/
"""

from __future__ import annotations

import sys
import json
import time
from pathlib import Path
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from config import (
    OHRC_IMG_PATH, OHRC_SHAPE, OHRC_DTYPE,
    LRO_IMG_PATH, SCALE_RATIO_LRO_TO_OHRC,
    FIGURES_DIR, MATCHES_PROCESSED_DIR,
)
from io_utils import load_ohrc_memmap, load_lro_nac_memmap, extract_patch
from preprocessing import percentile_stretch_uint8
from matching import LoFTRMatcher, save_matches_npz, load_matches_npz
from matching_lightglue import LightGlueFeatureMatcher
from spatial_uniformity import filter_spatial_uniformity
from transform import estimate_transform
from evaluate import calculate_reprojection_errors, calculate_spatial_metrics, cross_validate_transform


# ── image regions (same as prior experiments) ─────────────────────────────
OHRC_ROW_RANGE = (30000, 45000)
OHRC_COL_RANGE = (2000, 8000)
LRO_ROW_RANGE  = (5500, 8500)
LRO_COL_RANGE  = (400, 1800)

# ── spatial uniformity config ─────────────────────────────────────────────
GRID_SIZE      = (4, 4)
TOP_K_PER_CELL = 10
MIN_CONF       = 0.0

# ── MAGSAC++ config ───────────────────────────────────────────────────────
RANSAC_THRESH = 4.0


# ── helpers ───────────────────────────────────────────────────────────────
def load_image_pair():
    ohrc_mm = load_ohrc_memmap(OHRC_IMG_PATH, shape=OHRC_SHAPE, dtype=OHRC_DTYPE)
    lro_mm, _ = load_lro_nac_memmap(LRO_IMG_PATH)

    ohrc_raw = extract_patch(ohrc_mm, OHRC_ROW_RANGE, OHRC_COL_RANGE)
    lro_raw  = extract_patch(lro_mm, LRO_ROW_RANGE, LRO_COL_RANGE)

    ohrc_norm = percentile_stretch_uint8(ohrc_raw)
    lro_norm  = percentile_stretch_uint8(lro_raw)

    target_w = int(round(ohrc_norm.shape[1] / SCALE_RATIO_LRO_TO_OHRC))
    target_h = int(round(ohrc_norm.shape[0] / SCALE_RATIO_LRO_TO_OHRC))
    ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)

    print(f"OHRC scaled: {ohrc_scaled.shape} | LRO: {lro_norm.shape}")
    return ohrc_scaled, lro_norm


def draw_matches_side_by_side(img_src, img_ref, pts_src, pts_ref, title, save_path):
    h1, w1 = img_src.shape
    h2, w2 = img_ref.shape
    canvas_h = max(h1, h2)
    canvas = np.zeros((canvas_h, w1 + w2), dtype=np.uint8)
    canvas[:h1, :w1] = img_src
    canvas[:h2, w1:] = img_ref

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.imshow(canvas, cmap="gray")
    ax.set_title(title, fontsize=11)

    colors = plt.cm.rainbow(np.linspace(0, 1, max(1, len(pts_src))))
    for i, (ps, pr) in enumerate(zip(pts_src, pts_ref)):
        ax.plot([ps[0], pr[0] + w1], [ps[1], pr[1]], color=colors[i], lw=1.0, alpha=0.7)
        ax.scatter([ps[0], pr[0] + w1], [ps[1], pr[1]], color=colors[i], s=15, zorder=4)

    ax.axis("off")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {save_path}")


def draw_occupancy(img, pts, grid_size, save_path, title="Spatial Occupancy"):
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(img, cmap="gray")
    h, w = img.shape
    for r in range(1, grid_size[0]):
        ax.axhline(r * h / grid_size[0], color="yellow", alpha=0.5, lw=1)
    for c in range(1, grid_size[1]):
        ax.axvline(c * w / grid_size[1], color="yellow", alpha=0.5, lw=1)
    if len(pts):
        ax.scatter(pts[:, 0], pts[:, 1], c="red", s=25, zorder=4)
    ax.set_title(f"{title} ({len(pts)} pts)")
    ax.axis("off")
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {save_path}")


def create_overlays(src_img, ref_img, M, prefix):
    try:
        M_inv = np.linalg.inv(M)
    except np.linalg.LinAlgError:
        print("  Overlay skipped: singular M")
        return
    warped = cv2.warpPerspective(src_img, M_inv, (ref_img.shape[1], ref_img.shape[0]))
    alpha_path = f"{prefix}_alpha.png"
    cv2.imwrite(alpha_path, cv2.addWeighted(ref_img, 0.5, warped, 0.5, 0))
    print(f"  Saved: {alpha_path}")

    checker = ref_img.copy()
    cs = 150
    h, w = ref_img.shape
    for y in range(0, h, cs):
        for x in range(0, w, cs):
            if ((x // cs) + (y // cs)) % 2:
                checker[y:min(y+cs,h), x:min(x+cs,w)] = warped[y:min(y+cs,h), x:min(x+cs,w)]
    cv2.imwrite(f"{prefix}_checker.png", checker)
    print(f"  Saved: {prefix}_checker.png")


def eval_pipeline(name, pts_src, pts_ref, img_shape, src_img, ref_img, prefix):
    """Apply spatial uniformity → MAGSAC++ → metrics for one matcher."""
    rows = []

    # ── Step 1: report confidence distribution
    conf_fake = np.ones(len(pts_src))   # LightGlue/LoFTR already filtered by conf
    sp_src, sp_ref, _, _ = filter_spatial_uniformity(
        pts_src, pts_ref, conf_fake, img_shape,
        grid_size=GRID_SIZE, top_k_per_cell=TOP_K_PER_CELL, min_conf=MIN_CONF,
    )
    print(f"  After spatial uniformity: {len(sp_src)} candidates ({len(pts_src)} raw)")

    for model in ["similarity", "affine", "homography"]:
        M, mask = estimate_transform(sp_src, sp_ref, model=model, ransac_reproj_threshold=RANSAC_THRESH)
        inl_src = sp_src[mask] if M is not None else np.empty((0, 2))
        inl_ref = sp_ref[mask] if M is not None else np.empty((0, 2))
        n_in = len(inl_src)
        n_cand = len(sp_src)
        ratio = n_in / n_cand if n_cand else 0.0

        if M is None or n_in < 4:
            rows.append({
                "Matcher": name, "Model": model,
                "Raw": len(pts_src), "Spatially_Filtered": n_cand,
                "Inliers": n_in, "Inlier_Ratio_%": 0,
                "Fwd_RMSE": None, "Bwd_RMSE": None, "Sym_RMSE": None,
                "CV_RMSE": None, "Hull_%": 0, "Grid_Occ_%": 0,
                "Status": "FAILED",
            })
            continue

        err  = calculate_reprojection_errors(inl_src, inl_ref, M)
        sp   = calculate_spatial_metrics(inl_src, img_shape)
        cv   = cross_validate_transform(inl_src, inl_ref, model=model, threshold=RANSAC_THRESH)

        rows.append({
            "Matcher": name, "Model": model,
            "Raw": len(pts_src), "Spatially_Filtered": n_cand,
            "Inliers": n_in, "Inlier_Ratio_%": round(ratio * 100, 1),
            "Fwd_RMSE": round(err["fwd_rmse"], 3),
            "Bwd_RMSE": round(err["bwd_rmse"], 3),
            "Sym_RMSE": round(err["sym_rmse"], 3),
            "CV_RMSE":  round(cv["cv_rmse"], 3) if cv["cv_rmse"] == cv["cv_rmse"] else None,
            "Hull_%":   round(sp["hull_coverage"], 1),
            "Grid_Occ_%": round(sp["grid_occupancy"], 1),
            "Status": "OK",
        })

        # Save figures for homography only
        if model == "homography":
            draw_matches_side_by_side(
                src_img, ref_img, inl_src, inl_ref,
                f"{name} | {n_in} inliers | Sym RMSE={err['sym_rmse']:.2f}px",
                FIGURES_DIR / f"{prefix}_matches.png",
            )
            draw_occupancy(
                src_img, inl_src, GRID_SIZE,
                FIGURES_DIR / f"{prefix}_occupancy.png", title=f"{name} inliers"
            )
            create_overlays(src_img, ref_img, M, str(FIGURES_DIR / prefix))

    return rows


# ── main ──────────────────────────────────────────────────────────────────
def main():
    METRICS_DIR = Path("outputs/metrics")
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("MATCHER BENCHMARK: LoFTR vs LightGlue (ALIKED)")
    print("=" * 70)

    src_img, ref_img = load_image_pair()
    img_shape = src_img.shape
    all_rows = []

    # ── LoFTR ────────────────────────────────────────────────────────────
    npz = MATCHES_PROCESSED_DIR / "raw_candidates.npz"
    if npz.exists():
        print("\n[LoFTR] Loading cached candidates...")
        pts_src_l, pts_ref_l, conf_l, _ = load_matches_npz(npz)
        print(f"[LoFTR] {len(pts_src_l)} candidates loaded from cache")
    else:
        print("\n[LoFTR] Running inference (no cache)...")
        t0 = time.time()
        matcher_l = LoFTRMatcher(pretrained="outdoor", max_dim=1024)
        pts_src_l, pts_ref_l, conf_l = matcher_l.match(src_img, ref_img, conf_threshold=0.0)
        print(f"[LoFTR] {len(pts_src_l)} candidates in {time.time()-t0:.1f}s")
        save_matches_npz(npz, pts_src_l, pts_ref_l, conf_l)

    print("\n[LoFTR] Evaluating pipeline...")
    all_rows.extend(eval_pipeline("LoFTR", pts_src_l, pts_ref_l, img_shape, src_img, ref_img, "loftr"))

    # ── LightGlue ────────────────────────────────────────────────────────
    npz_lg = MATCHES_PROCESSED_DIR / "raw_candidates_lightglue.npz"
    if npz_lg.exists():
        print("\n[LightGlue] Loading cached candidates...")
        pts_src_g, pts_ref_g, conf_g, _ = load_matches_npz(npz_lg)
        print(f"[LightGlue] {len(pts_src_g)} candidates loaded from cache")
    else:
        print("\n[LightGlue] Running ALIKED+LightGlue inference...")
        t0 = time.time()
        matcher_g = LightGlueFeatureMatcher(max_dim=1024, max_keypoints=2048)
        pts_src_g, pts_ref_g, conf_g = matcher_g.match(src_img, ref_img, conf_threshold=0.0)
        print(f"[LightGlue] {len(pts_src_g)} candidates in {time.time()-t0:.1f}s")
        save_matches_npz(npz_lg, pts_src_g, pts_ref_g, conf_g)

    print("\n[LightGlue] Evaluating pipeline...")
    all_rows.extend(eval_pipeline("LightGlue", pts_src_g, pts_ref_g, img_shape, src_img, ref_img, "lightglue"))

    # ── Report ────────────────────────────────────────────────────────────
    df = pd.DataFrame(all_rows)
    df.to_csv(METRICS_DIR / "matcher_benchmark.csv", index=False)
    df.to_json(METRICS_DIR / "matcher_benchmark.json", orient="records", indent=2)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", None)
    print(df[["Matcher", "Model", "Raw", "Inliers", "Grid_Occ_%", "Hull_%", "Sym_RMSE", "CV_RMSE", "Status"]])
    print(f"\nSaved: outputs/metrics/matcher_benchmark.csv")
    print(f"Saved: outputs/figures/loftr_*.png + lightglue_*.png")


if __name__ == "__main__":
    main()
