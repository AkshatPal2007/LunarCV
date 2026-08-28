"""
Phase 3/4 — Scale-Matched Source (TMC-2) & Reference (LRO NAC) Pipeline.

Pipeline:
    1. Load TMC-2 source patch (4000x2000 uint16 @ ~5.0 m/px).
    2. Load LRO NAC full reference strip (52224x5064 uint8 @ ~0.5 m/px).
    3. Downsample LRO NAC by 10x to match TMC-2 scale (~5.0 m/px, 5222x506 px).
    4. Extract matching column corridor and run CLAHE preprocessing on both.
    5. Run LoFTR feature matching on scale-aligned images.
    6. Filter matches with OpenCV MAGSAC++ outlier rejection.
    7. Save preprocessed arrays, inliers, homography matrix, and visualization figure.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import (
    TMC2_IMG_PATH,
    TMC2_SHAPE,
    TMC2_DTYPE,
    LRO_IMG_PATH,
    TMC2_PROCESSED_DIR,
    LRO_PROCESSED_DIR,
    FIGURES_DIR,
)
from io_utils import (
    load_tmc2_memmap,
    load_lro_nac_memmap,
    extract_patch,
    print_patch_stats,
)
from preprocessing import (
    normalize_uint16_to_uint8,
    apply_clahe,
    save_comparison_figure,
)
from matching import LoFTRMatcher
from outlier_rejection import magsac_filter, print_match_stats

# ---------------------------------------------------------------------------
# Pipeline Configuration
# ---------------------------------------------------------------------------
TMC2_ROW_RANGE = (50000, 54000)
TMC2_COL_RANGE = (1000, 3000)

PATCH_LABEL = f"r{TMC2_ROW_RANGE[0]}-{TMC2_ROW_RANGE[1]}_c{TMC2_COL_RANGE[0]}-{TMC2_COL_RANGE[1]}"

CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID  = (8, 8)

LOFTR_CONF_THRESHOLD = 0.35
MAGSAC_REPROJ_THRESH = 5.0


def main() -> None:
    print("=" * 65)
    print("LunarCV Phase 3/4 — Scale-Matched Pair Preprocessing & Feature Matching")
    print("=" * 65)

    # ------------------------------------------------------------------
    # 1. Load TMC-2 Source Patch (5.0 m/px)
    # ------------------------------------------------------------------
    print(f"\n[1/6] Loading TMC-2 raw image: {TMC2_IMG_PATH.name}")
    tmc2_memmap = load_tmc2_memmap(TMC2_IMG_PATH, shape=TMC2_SHAPE, dtype=TMC2_DTYPE)
    tmc2_raw = extract_patch(tmc2_memmap, TMC2_ROW_RANGE, TMC2_COL_RANGE)
    print_patch_stats(tmc2_raw, label="TMC-2 raw uint16 patch (5 m/px)")

    tmc2_norm = normalize_uint16_to_uint8(tmc2_raw, p_low=2.0, p_high=98.0)
    tmc2_clahe = apply_clahe(tmc2_norm, clip_limit=CLAHE_CLIP_LIMIT, tile_grid_size=CLAHE_TILE_GRID)

    # ------------------------------------------------------------------
    # 2. Load & 10x Scale-Match LRO NAC Reference (0.5 m/px -> 5.0 m/px)
    # ------------------------------------------------------------------
    print(f"\n[2/6] Loading LRO NAC image: {LRO_IMG_PATH.name}")
    lro_memmap, lro_meta = load_lro_nac_memmap(LRO_IMG_PATH)
    print(f"      LRO raw strip shape: {lro_memmap.shape} @ ~0.5 m/px")

    print("      Downsampling LRO NAC by 10x to match TMC-2 scale (~5.0 m/px) ...")
    lro_full = np.array(lro_memmap)
    lro_down = cv2.resize(
        lro_full,
        (lro_full.shape[1] // 10, lro_full.shape[0] // 10),
        interpolation=cv2.INTER_AREA,
    )
    lro_clahe = apply_clahe(lro_down, clip_limit=CLAHE_CLIP_LIMIT, tile_grid_size=CLAHE_TILE_GRID)
    print_patch_stats(lro_clahe, label="LRO NAC downsampled CLAHE strip (5 m/px)")

    # ------------------------------------------------------------------
    # 3. Save Scale-Matched Preprocessed Arrays
    # ------------------------------------------------------------------
    print("\n[3/6] Saving preprocessed arrays (.npy) ...")
    tmc2_npy = TMC2_PROCESSED_DIR / f"tmc2_patch_{PATCH_LABEL}_clahe.npy"
    lro_npy  = LRO_PROCESSED_DIR / f"lro_{LRO_IMG_PATH.stem}_scale_matched_clahe.npy"

    np.save(tmc2_npy, tmc2_clahe)
    np.save(lro_npy, lro_clahe)
    print(f"  [npy] TMC-2 preprocessed array  -> {tmc2_npy}")
    print(f"  [npy] LRO NAC scale-matched array -> {lro_npy}")

    # ------------------------------------------------------------------
    # 4. Run Detector-Free LoFTR Matching
    # ------------------------------------------------------------------
    print("\n[4/6] Running LoFTR feature matching on scale-matched pair ...")
    matcher = LoFTRMatcher(pretrained="outdoor", max_dim=1024)
    mkpts_src, mkpts_ref, conf = matcher.match(
        tmc2_clahe,
        lro_clahe,
        conf_threshold=LOFTR_CONF_THRESHOLD,
    )
    print_match_stats(mkpts_src, mkpts_ref, conf, label="LoFTR Candidates")

    # ------------------------------------------------------------------
    # 5. MAGSAC++ Outlier Rejection
    # ------------------------------------------------------------------
    print("\n[5/6] Running MAGSAC++ outlier rejection ...")
    mkpts_src_clean, mkpts_ref_clean, conf_clean, H, mask = magsac_filter(
        mkpts_src,
        mkpts_ref,
        conf,
        model="homography",
        ransac_reproj_threshold=MAGSAC_REPROJ_THRESH,
    )
    print_match_stats(mkpts_src_clean, mkpts_ref_clean, conf_clean, label="Inliers after MAGSAC++")

    # ------------------------------------------------------------------
    # 6. Save Matches & Visualization Figure
    # ------------------------------------------------------------------
    print("\n[6/6] Saving match results & figures ...")
    match_dir = TMC2_PROCESSED_DIR.parent / "matches"
    match_dir.mkdir(parents=True, exist_ok=True)

    np.save(match_dir / f"mkpts_src_{PATCH_LABEL}.npy", mkpts_src_clean)
    np.save(match_dir / f"mkpts_ref_{PATCH_LABEL}.npy", mkpts_ref_clean)
    if H is not None:
        np.save(match_dir / f"homography_{PATCH_LABEL}.npy", H)
        print("  [npy] Homography matrix saved.")

    fig_pair = FIGURES_DIR / "tmc2_vs_lro_pair_preprocessed.png"
    save_comparison_figure(
        img_left=tmc2_clahe,
        img_right=lro_clahe,
        title_left="Source: Chandrayaan-2 TMC-2 (5 m/px)",
        title_right=f"Reference: LRO NAC {LRO_IMG_PATH.stem} (Scale-matched 5 m/px)",
        save_path=fig_pair,
        suptitle="LunarCV Phase 3 — Scale-Matched Source & Reference Preprocessing"
    )

    fig_match = FIGURES_DIR / "loftr_magsac_matches.png"
    _draw_connected_matches(tmc2_clahe, lro_clahe, mkpts_src_clean, mkpts_ref_clean, fig_match)

    print("\n" + "=" * 65)
    print("SCALE-MATCHED PIPELINE COMPLETE")
    print(f"  Candidate matches  : {len(conf)}")
    print(f"  Inliers (MAGSAC++) : {len(mkpts_src_clean)}")
    print(f"  Match figure       : {fig_match}")
    print("=" * 65)


def _draw_connected_matches(
    img_src: np.ndarray,
    img_ref: np.ndarray,
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    save_path: Path,
) -> None:
    """Draw side-by-side matching figure with connected correspondence lines."""
    h_src, w_src = img_src.shape
    h_ref, w_ref = img_ref.shape

    # Canvas height = max(h_src, h_ref), Canvas width = w_src + w_ref
    canvas_h = max(h_src, h_ref)
    canvas_w = w_src + w_ref

    fig, ax = plt.subplots(figsize=(16, 10))
    canvas = np.zeros((canvas_h, canvas_w), dtype=np.uint8)

    canvas[:h_src, :w_src] = img_src
    canvas[:h_ref, w_src:w_src + w_ref] = img_ref

    ax.imshow(canvas, cmap="gray")
    ax.set_title(
        f"Scale-Matched LoFTR + MAGSAC++ Inliers ({len(pts_src)} Correspondences)",
        fontsize=13,
        fontweight="bold",
    )

    # Draw connected lines between matching keypoints
    colors = plt.cm.rainbow(np.linspace(0, 1, max(1, len(pts_src))))
    for i, (p_src, p_ref) in enumerate(zip(pts_src, pts_ref)):
        x1, y1 = p_src[0], p_src[1]
        x2, y2 = p_ref[0] + w_src, p_ref[1]
        c = colors[i]

        ax.plot([x1, x2], [y1, y2], color=c, linewidth=1.2, alpha=0.8)
        ax.scatter([x1, x2], [y1, y2], color=c, s=15, zorder=3)

    ax.set_xlim(0, canvas_w)
    ax.set_ylim(canvas_h, 0)
    ax.axis("off")

    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [fig] Connected match figure -> {save_path}")


if __name__ == "__main__":
    main()