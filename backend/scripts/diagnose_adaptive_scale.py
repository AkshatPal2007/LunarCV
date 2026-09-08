"""
diagnose_adaptive_scale.py — Per-chunk adaptive scale search.

For each of 12 chunks, try a grid of (sx, sy) scale factors around the
empirical baseline (10.5, 4.55).  Pick the scale that maximizes RANSAC
inlier count per chunk, then report:
  - best scale per chunk
  - whether the optimal scale varies along Y (pushbroom drift)
  - total inlier count and spatial coverage vs. fixed-scale baseline

Uses LightGlue only for the search phase (RIFT2 contributed 0 matches in
all prior tests, so omitting it here avoids 12×9 unnecessary RIFT2 calls).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lunarcv.config import (
    OHRC_IMG_PATH, OHRC_SHAPE, OHRC_DTYPE,
    LRO_IMG_PATH,
    SCALE_X_LRO_TO_OHRC, SCALE_Y_LRO_TO_OHRC,
    FIGURES_DIR, SUBMISSION_DIR,
)
from lunarcv.io.raster import load_ohrc_memmap, load_lro_nac_memmap, extract_patch
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher


def percentile_stretch_uint8(img, p_low=1.0, p_high=99.0):
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    return np.clip((img.astype(np.float32) - v_min) / (v_max - v_min) * 255, 0, 255).astype(np.uint8)


def decompose_affine(M):
    a, b, tx = M[0, 0], M[0, 1], M[0, 2]
    c, d, ty = M[1, 0], M[1, 1], M[1, 2]
    det = a * d - b * c
    sx = np.sqrt(a**2 + c**2)
    sy = np.sqrt(b**2 + d**2)
    if det < 0:
        sx = -sx
    rot = np.degrees(np.arctan2(c, a))
    return tx, ty, sx, sy, rot, det


def is_degenerate(n_inliers, det, sx, sy, rot, rmse):
    if n_inliers < 5:
        return "insufficient geometric support"
    if abs(det) < 0.01:
        return "degenerate determinant"
    if sx < 0.01 or sy < 0.01 or sx > 2.0 or sy > 2.0:
        return f"absurd scale ({sx:.3f}, {sy:.3f})"
    if abs(rot) > 45.0:
        return f"extreme rotation ({rot:.1f}°)"
    if rmse > 10.0:
        return f"excessive RMSE ({rmse:.1f}px)"
    return None


def try_scale(matcher, ohrc_norm, lro_norm, chunk_y_range_frac, sx, sy):
    """
    Resize the FULL OHRC crop at (sx, sy), cut the chunk from the scaled
    image, match against the corresponding LRO chunk, and return inlier stats.

    chunk_y_range_frac: (frac_start, frac_end) in [0, 1] — fraction of the
    image height that this chunk spans.
    """
    h_ohrc, w_ohrc = ohrc_norm.shape
    h_lro, w_lro = lro_norm.shape

    target_w = max(16, int(round(w_ohrc / sx)))
    target_h = max(16, int(round(h_ohrc / sy)))
    ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)

    frac_start, frac_end = chunk_y_range_frac
    y1_src = int(round(frac_start * target_h))
    y2_src = min(int(round(frac_end * target_h)), target_h)
    y1_ref = int(round(frac_start * h_lro))
    y2_ref = min(int(round(frac_end * h_lro)), h_lro)

    patch_src = ohrc_scaled[y1_src:y2_src, :]
    patch_ref = lro_norm[y1_ref:y2_ref, :]

    if patch_src.shape[0] < 32 or patch_ref.shape[0] < 32:
        return 0, 0, 0.0, None, None, None

    pts_src, pts_ref, conf = matcher.match(patch_src, patch_ref, conf_threshold=0.0)
    n_raw = len(pts_src)

    if n_raw < 4:
        return n_raw, 0, 0.0, None, None, None

    # Map to global coordinates
    pts_src_g = pts_src.copy()
    pts_src_g[:, 1] += y1_src
    pts_ref_g = pts_ref.copy()
    pts_ref_g[:, 1] += y1_ref

    # Map source back to ORIGINAL OHRC coordinates
    pts_src_orig = pts_src_g.copy()
    pts_src_orig[:, 0] *= sx
    pts_src_orig[:, 1] *= sy

    M, raw_mask = cv2.estimateAffine2D(
        pts_src_orig, pts_ref_g, method=cv2.RANSAC, ransacReprojThreshold=15.0,
    )
    if M is None:
        return n_raw, 0, 0.0, None, None, None

    mask = raw_mask.ravel().astype(bool)
    n_in = int(mask.sum())

    rmse = 0.0
    if n_in > 0:
        hom = np.hstack([pts_src_orig[mask], np.ones((n_in, 1))])
        proj = (M @ hom.T).T
        rmse = float(np.sqrt(np.mean(np.sum((proj - pts_ref_g[mask]) ** 2, axis=1))))

    return n_raw, n_in, rmse, M, pts_src_orig[mask], pts_ref_g[mask]


def main():
    print("=" * 70)
    print("PER-CHUNK ADAPTIVE SCALE SEARCH")
    print("=" * 70)

    ohrc_mm = load_ohrc_memmap(OHRC_IMG_PATH, shape=OHRC_SHAPE, dtype=OHRC_DTYPE)
    lro_mm, _ = load_lro_nac_memmap(LRO_IMG_PATH)

    ohrc_raw = extract_patch(ohrc_mm, (30000, 45000), (2000, 8000))
    lro_raw = extract_patch(lro_mm, (5500, 8500), (400, 1800))
    ohrc_norm = percentile_stretch_uint8(ohrc_raw)
    lro_norm = percentile_stretch_uint8(lro_raw)

    # Scale search grid
    sx_base = SCALE_X_LRO_TO_OHRC  # 10.5
    sy_base = SCALE_Y_LRO_TO_OHRC  # 4.55

    sx_grid = [sx_base * 0.85, sx_base, sx_base * 1.15]           # ~[8.9, 10.5, 12.1]
    sy_grid = [sy_base * 0.75, sy_base * 0.88, sy_base,
               sy_base * 1.12, sy_base * 1.25]                    # ~[3.4, 4.0, 4.55, 5.1, 5.7]

    scale_combos = [(sxi, syi) for sxi in sx_grid for syi in sy_grid]
    print(f"Scale grid: {len(sx_grid)} sx × {len(sy_grid)} sy = {len(scale_combos)} combos per chunk")
    print(f"  sx: {[f'{s:.2f}' for s in sx_grid]}")
    print(f"  sy: {[f'{s:.2f}' for s in sy_grid]}")

    # Chunking: 12 chunks with ~20% overlap (same fractions as before)
    n_chunks = 12
    overlap_frac = 0.16  # overlap as fraction of chunk height
    chunk_step = 1.0 / n_chunks
    chunk_ranges = []
    for i in range(n_chunks):
        frac_start = max(0.0, i * chunk_step - overlap_frac / 2)
        frac_end = min(1.0, (i + 1) * chunk_step + overlap_frac / 2)
        chunk_ranges.append((frac_start, frac_end))

    matcher = LightGlueFeatureMatcher(max_dim=1500, max_keypoints=2048)

    best_results = []

    for ci, (frac_s, frac_e) in enumerate(chunk_ranges):
        chunk_id = ci + 1
        y_center_orig = (frac_s + frac_e) / 2 * ohrc_norm.shape[0]

        print(f"\n--- Chunk {chunk_id:02d}  (OHRC frac {frac_s:.3f}–{frac_e:.3f}, "
              f"Y-center ≈ {y_center_orig:.0f}) ---")

        best_in = 0
        best_raw = 0
        best_rmse = 999.0
        best_sx = sx_base
        best_sy = sy_base
        best_M = None
        best_src = None
        best_ref = None

        for sxi, syi in scale_combos:
            n_raw, n_in, rmse, M, src_pts, ref_pts = try_scale(
                matcher, ohrc_norm, lro_norm, (frac_s, frac_e), sxi, syi,
            )
            # Primary criterion: max inliers.  Tiebreak: lower RMSE.
            if n_in > best_in or (n_in == best_in and n_in > 0 and rmse < best_rmse):
                best_in = n_in
                best_raw = n_raw
                best_rmse = rmse
                best_sx = sxi
                best_sy = syi
                best_M = M
                best_src = src_pts
                best_ref = ref_pts

        # Degeneracy check on best
        status = "REJECTED"
        reason = "no matches"
        if best_M is not None:
            tx, ty, asx, asy, rot, det = decompose_affine(best_M)
            reason_str = is_degenerate(best_in, det, asx, asy, rot, best_rmse)
            if reason_str is None:
                status = "ACCEPTED"
                reason = ""
            else:
                reason = reason_str
        else:
            tx = ty = asx = asy = rot = det = 0.0

        flag = "✓" if status == "ACCEPTED" else "✗"
        print(f"  Best scale: sx={best_sx:.2f}  sy={best_sy:.2f}  "
              f"(Δsx={best_sx - sx_base:+.2f}  Δsy={best_sy - sy_base:+.2f})")
        print(f"  [{flag}]  raw={best_raw:3d}  inliers={best_in:2d}  "
              f"RMSE={best_rmse:.2f}  det={det:.4f}  "
              f"{'  ' + reason if status == 'REJECTED' else ''}")

        best_results.append(dict(
            chunk_id=chunk_id, y_center_orig=y_center_orig,
            best_sx=best_sx, best_sy=best_sy,
            raw=best_raw, inliers=best_in, rmse=best_rmse,
            status=status, reason=reason,
            affine=best_M, pts_src=best_src, pts_ref=best_ref,
            det=det, aff_sx=asx, aff_sy=asy, rot=rot, tx=tx, ty=ty,
        ))

    # ── Summary ──────────────────────────────────────────────────────────
    accepted = [r for r in best_results if r["status"] == "ACCEPTED"]
    rejected = [r for r in best_results if r["status"] == "REJECTED"]

    print("\n" + "=" * 70)
    print("ADAPTIVE SCALE SEARCH — SUMMARY")
    print("=" * 70)
    print(f"Accepted: {len(accepted)} / {n_chunks}")
    print(f"Rejected: {len(rejected)} / {n_chunks}")

    total_raw = sum(r["raw"] for r in best_results)
    total_in = sum(r["inliers"] for r in accepted)

    # Deduplicate control points
    if accepted:
        all_src = np.vstack([r["pts_src"] for r in accepted])
        all_ref = np.vstack([r["pts_ref"] for r in accepted])
        # Greedy dedup radius=20px
        keep = np.ones(len(all_src), dtype=bool)
        for i in range(len(all_src)):
            if not keep[i]:
                continue
            dists = np.linalg.norm(all_src[i + 1:] - all_src[i], axis=1)
            keep[np.where(dists < 20)[0] + i + 1] = False
        src_u = all_src[keep]
        ref_u = all_ref[keep]
        n_unique = len(src_u)

        h_o, w_o = ohrc_norm.shape
        bins_y = np.linspace(0, h_o, 5)
        bins_x = np.linspace(0, w_o, 5)
        grid, _, _ = np.histogram2d(src_u[:, 1], src_u[:, 0], bins=[bins_y, bins_x])
        occ = int(np.count_nonzero(grid))
        min_y, max_y = src_u[:, 1].min(), src_u[:, 1].max()
        min_x, max_x = src_u[:, 0].min(), src_u[:, 0].max()
        cov = 100.0 * (max_x - min_x) * (max_y - min_y) / (h_o * w_o)
    else:
        n_unique = 0
        occ = 0
        cov = 0.0
        grid = np.zeros((4, 4))

    # Comparison table
    print(f"\n{'Method':<25} | {'Chunks':>6} | {'Raw':>5} | {'Inliers':>7} | {'Unique':>6} | {'Coverage':>8} | {'Grid':>6}")
    print("-" * 75)
    print(f"{'Fixed scale (baseline)':<25} | {'12':>6} | {'124':>5} | {'27':>7} | {'23':>6} | {'40.3%':>8} | {'5/16':>6}")
    print(f"{'Adaptive scale':<25} | {n_chunks:>6} | {total_raw:>5} | {total_in:>7} | {n_unique:>6} | {cov:>7.1f}% | {occ:>2}/16")
    print("=" * 75)

    if n_unique > 0:
        print(f"\nDeduplicated control points: {n_unique}")
        print(f"  X range: [{min_x:.0f}, {max_x:.0f}]")
        print(f"  Y range: [{min_y:.0f}, {max_y:.0f}]")
        print(f"  Grid:\n{grid.astype(int)}")

    # ── Optimal scale vs Y-center plot ───────────────────────────────────
    y_centers = [r["y_center_orig"] for r in best_results]
    opt_sx = [r["best_sx"] for r in best_results]
    opt_sy = [r["best_sy"] for r in best_results]
    inliers_per = [r["inliers"] for r in best_results]
    colors = ["green" if r["status"] == "ACCEPTED" else "red" for r in best_results]

    fig, axes = plt.subplots(3, 1, figsize=(12, 14), sharex=True)

    axes[0].scatter(y_centers, opt_sx, c=colors, s=60, zorder=5)
    axes[0].axhline(sx_base, color="gray", ls="--", alpha=0.5, label=f"baseline sx={sx_base:.1f}")
    axes[0].set_ylabel("Best Scale X")
    axes[0].set_title("Per-Chunk Optimal Scale vs OHRC Y-Position")
    axes[0].legend()

    axes[1].scatter(y_centers, opt_sy, c=colors, s=60, zorder=5)
    axes[1].axhline(sy_base, color="gray", ls="--", alpha=0.5, label=f"baseline sy={sy_base:.2f}")
    axes[1].set_ylabel("Best Scale Y")
    axes[1].legend()

    axes[2].bar(y_centers, inliers_per, width=600, color=colors, alpha=0.7)
    axes[2].set_ylabel("RANSAC Inliers")
    axes[2].set_xlabel("OHRC Y-Coordinate (original)")

    plt.tight_layout()
    plt.savefig(str(FIGURES_DIR / "adaptive_scale_vs_y.png"), dpi=150)
    plt.close()
    print(f"\nSaved: {FIGURES_DIR / 'adaptive_scale_vs_y.png'}")

    # ── Save updated control points ──────────────────────────────────────
    if n_unique > 0:
        csv_path = SUBMISSION_DIR / "control_points_adaptive.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ohrc_x", "ohrc_y", "lro_x", "lro_y"])
            for s, r in zip(src_u, ref_u):
                w.writerow([f"{s[0]:.2f}", f"{s[1]:.2f}", f"{r[0]:.2f}", f"{r[1]:.2f}"])
        print(f"Saved: {csv_path}")

        # Coverage scatter
        plt.figure(figsize=(6, 12))
        plt.scatter(src_u[:, 0], src_u[:, 1], c="red", s=8, zorder=5)
        plt.xlim(0, w_o)
        plt.ylim(h_o, 0)
        plt.title(f"Adaptive-Scale Control Points ({n_unique} pts)")
        plt.xlabel("OHRC X")
        plt.ylabel("OHRC Y")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(str(FIGURES_DIR / "control_points_adaptive.png"), dpi=150)
        plt.close()
        print(f"Saved: {FIGURES_DIR / 'control_points_adaptive.png'}")

    # ── Per-chunk table ──────────────────────────────────────────────────
    print(f"\n{'Chunk':>5} | {'Y-center':>8} | {'sx':>6} | {'sy':>6} | {'Δsy':>6} | {'Raw':>4} | {'In':>3} | {'RMSE':>6} | Status")
    print("-" * 75)
    for r in best_results:
        flag = "✓" if r["status"] == "ACCEPTED" else "✗"
        dsy = r["best_sy"] - sy_base
        print(f"  {r['chunk_id']:3d} | {r['y_center_orig']:8.0f} | {r['best_sx']:6.2f} | "
              f"{r['best_sy']:6.2f} | {dsy:+6.2f} | {r['raw']:4d} | {r['inliers']:3d} | "
              f"{r['rmse']:6.2f} | [{flag}] {r['reason']}")


if __name__ == "__main__":
    main()
