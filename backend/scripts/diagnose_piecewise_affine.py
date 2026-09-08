"""
diagnose_piecewise_affine.py — Piecewise affine registration prototype.

Reuses the dense-chunking logic from diagnose_dense_chunking.py to:
1. Run 12-chunk local matching with LightGlue + RIFT2.
2. Estimate local affine transforms per chunk with degeneracy checks.
3. Blend overlapping warped chunks into a single piecewise-affine registered image.
4. Compare against the global affine warp from the baseline pipeline.
5. Measure residual consistency and neighbor-transform agreement.
6. Deduplicate control points and save for future nonlinear fitting.
"""

from __future__ import annotations

import csv
import json
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
from lunarcv.matching.ensemble import EnsembleMatcher
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.matching.rift2_matcher import RIFT2Matcher

# ── Shared helpers (same as diagnose_dense_chunking.py) ──────────────────────

def percentile_stretch_uint8(img: np.ndarray, p_low: float = 1.0, p_high: float = 99.0) -> np.ndarray:
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    stretched = np.clip((img.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255)
    return stretched.astype(np.uint8)


def decompose_affine(M: np.ndarray):
    """Decompose 2x3 affine matrix into translation, scale, rotation, determinant."""
    a, b, tx = M[0, 0], M[0, 1], M[0, 2]
    c, d, ty = M[1, 0], M[1, 1], M[1, 2]
    det = a * d - b * c
    sx = np.sqrt(a**2 + c**2)
    sy = np.sqrt(b**2 + d**2)
    if det < 0:
        sx = -sx
    rot_deg = np.degrees(np.arctan2(c, a))
    return tx, ty, sx, sy, rot_deg, det


# ── Per-chunk matching and affine estimation ─────────────────────────────────

def run_chunk(matcher, ohrc_scaled, lro_norm, y1_src, y2_src, y1_ref, y2_ref,
              chunk_id, sx, sy):
    """Match one chunk and fit a local affine. Returns a result dict."""
    patch_src = ohrc_scaled[y1_src:y2_src, :]
    patch_ref = lro_norm[y1_ref:y2_ref, :]
    y_center_orig = (y1_src + (y2_src - y1_src) / 2) * sy

    pts_src, pts_ref, conf = matcher.match(patch_src, patch_ref, conf_threshold=0.0)

    res = dict(
        chunk_id=chunk_id,
        y_center_orig=y_center_orig,
        ohrc_bounds_scaled=(y1_src, y2_src),
        lro_bounds=(y1_ref, y2_ref),
        raw_matches=len(pts_src),
        status="REJECTED", reason="Insufficient matches (< 4)",
        inliers=0, inlier_ratio=0.0, rmse=0.0,
        affine=None,
        pts_src_orig=None, pts_ref_orig=None,
        det=0.0, tx=0.0, ty=0.0, sx_aff=0.0, sy_aff=0.0, rot=0.0,
    )

    if len(pts_src) < 4:
        return res

    # Map to global coordinates
    pts_src_scaled = pts_src.copy()
    pts_src_scaled[:, 1] += y1_src
    pts_ref_global = pts_ref.copy()
    pts_ref_global[:, 1] += y1_ref

    # Map source to original OHRC coordinates
    pts_src_orig = pts_src_scaled.copy()
    pts_src_orig[:, 0] *= sx
    pts_src_orig[:, 1] *= sy

    M, raw_mask = cv2.estimateAffine2D(
        pts_src_orig, pts_ref_global, method=cv2.RANSAC, ransacReprojThreshold=15.0,
    )
    if M is None:
        res["reason"] = "RANSAC model estimation failed"
        return res

    mask = raw_mask.ravel().astype(bool)
    n_in = int(mask.sum())
    res["inliers"] = n_in
    res["inlier_ratio"] = n_in / len(pts_src) if len(pts_src) else 0.0

    tx, ty, scale_x, scale_y, rot, det = decompose_affine(M)
    res.update(tx=tx, ty=ty, sx_aff=scale_x, sy_aff=scale_y, rot=rot, det=det)

    if n_in > 0:
        pts_src_in = pts_src_orig[mask]
        pts_ref_in = pts_ref_global[mask]
        pts_hom = np.hstack([pts_src_in, np.ones((n_in, 1))])
        projected = (M @ pts_hom.T).T
        err = np.linalg.norm(projected - pts_ref_in, axis=1)
        res["rmse"] = float(np.sqrt(np.mean(err**2)))
        res["pts_src_orig"] = pts_src_in
        res["pts_ref_orig"] = pts_ref_in

    # Degeneracy checks
    if n_in < 5:
        res["reason"] = "insufficient geometric support"
    elif abs(det) < 0.01:
        res["reason"] = "degenerate determinant (near zero)"
    elif scale_x < 0.01 or scale_y < 0.01 or scale_x > 2.0 or scale_y > 2.0:
        res["reason"] = f"absurd scale (sx={scale_x:.3f}, sy={scale_y:.3f})"
    elif abs(rot) > 45.0:
        res["reason"] = f"extreme rotation ({rot:.1f} deg)"
    elif res["rmse"] > 10.0:
        res["reason"] = f"excessive reprojection error ({res['rmse']:.1f}px)"
    else:
        res["status"] = "ACCEPTED"
        res["reason"] = ""
        res["affine"] = M

    return res


# ── Piecewise affine warping with linear feathering ──────────────────────────

def piecewise_affine_warp(ohrc_norm, lro_norm, results, sx, sy):
    """
    Warp OHRC strips into LRO space using per-chunk affine transforms,
    blending overlapping regions with distance-to-chunk-center weighting.
    """
    h_ref, w_ref = lro_norm.shape
    canvas = np.zeros((h_ref, w_ref), dtype=np.float64)
    weight_sum = np.zeros((h_ref, w_ref), dtype=np.float64)

    accepted = [r for r in results if r["status"] == "ACCEPTED"]
    if not accepted:
        print("[piecewise] No accepted chunks — cannot warp.")
        return None

    for r in accepted:
        M = r["affine"]
        y1_s, y2_s = r["ohrc_bounds_scaled"]
        y1_o = int(y1_s * sy)
        y2_o = int(y2_s * sy)

        # Extract original OHRC strip for this chunk
        ohrc_strip = ohrc_norm[y1_o:y2_o, :]
        if ohrc_strip.size == 0:
            continue

        # Warp into LRO coordinate frame
        warped = cv2.warpAffine(ohrc_strip, M, (w_ref, h_ref),
                                flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        valid_mask = warped > 0

        # Build a weight map: linear ramp from 0 at strip edges to 1 at center
        strip_h = y2_o - y1_o
        ramp = np.linspace(0, 1, strip_h // 2 + 1)
        ramp = np.concatenate([ramp, ramp[-2::-1]])  # symmetric triangle
        if len(ramp) < strip_h:
            ramp = np.append(ramp, [0] * (strip_h - len(ramp)))
        ramp = ramp[:strip_h]
        weight_strip = np.outer(ramp, np.ones(ohrc_norm.shape[1]))
        weight_warped = cv2.warpAffine(weight_strip.astype(np.float32), M,
                                       (w_ref, h_ref),
                                       flags=cv2.INTER_CUBIC,
                                       borderMode=cv2.BORDER_CONSTANT,
                                       borderValue=0)
        weight_warped[~valid_mask] = 0.0

        canvas += warped.astype(np.float64) * weight_warped
        weight_sum += weight_warped

    # Normalize
    mask_valid = weight_sum > 0
    result = np.zeros_like(canvas, dtype=np.uint8)
    result[mask_valid] = np.clip(canvas[mask_valid] / weight_sum[mask_valid], 0, 255).astype(np.uint8)

    valid_pct = 100.0 * mask_valid.sum() / mask_valid.size
    print(f"[piecewise] Valid warped pixels: {mask_valid.sum()} / {mask_valid.size} ({valid_pct:.1f}%)")

    return result, mask_valid


# ── Neighbor consistency ─────────────────────────────────────────────────────

def neighbor_consistency(results, sy):
    """
    For each pair of neighboring accepted chunks, compare their affine
    transforms over a set of test points in the overlap region.
    """
    accepted = [r for r in results if r["status"] == "ACCEPTED"]
    if len(accepted) < 2:
        print("[neighbor] Fewer than 2 accepted chunks — no pairs to compare.")
        return

    print("\n--- Neighbor Transform Consistency ---")
    for i in range(len(accepted) - 1):
        a, b = accepted[i], accepted[i + 1]
        Ma, Mb = a["affine"], b["affine"]

        # Overlap region in original OHRC Y
        y_top_a, y_bot_a = a["ohrc_bounds_scaled"][0] * sy, a["ohrc_bounds_scaled"][1] * sy
        y_top_b, y_bot_b = b["ohrc_bounds_scaled"][0] * sy, b["ohrc_bounds_scaled"][1] * sy
        overlap_top = max(y_top_a, y_top_b)
        overlap_bot = min(y_bot_a, y_bot_b)

        if overlap_bot <= overlap_top:
            print(f"  Chunks {a['chunk_id']}-{b['chunk_id']}: no spatial overlap")
            continue

        # Sample test points in the overlap region
        test_ys = np.linspace(overlap_top, overlap_bot, 5)
        test_xs = np.array([1000, 3000, 5000])
        test_pts = np.array([[x, y] for y in test_ys for x in test_xs], dtype=np.float64)
        hom = np.hstack([test_pts, np.ones((len(test_pts), 1))])

        proj_a = (Ma @ hom.T).T
        proj_b = (Mb @ hom.T).T
        diffs = np.linalg.norm(proj_a - proj_b, axis=1)

        print(f"  Chunks {a['chunk_id']:02d}→{b['chunk_id']:02d}  "
              f"overlap: {overlap_top:.0f}–{overlap_bot:.0f} px  "
              f"projection diff: mean={diffs.mean():.1f} px  max={diffs.max():.1f} px")


# ── Deduplication ────────────────────────────────────────────────────────────

def deduplicate_control_points(results, ohrc_shape, radius=20.0):
    """
    Pool all verified correspondences. Remove duplicate physical points
    from overlapping chunks (within `radius` pixels in OHRC space).
    """
    all_src, all_ref = [], []
    for r in results:
        if r["status"] == "ACCEPTED" and r["pts_src_orig"] is not None:
            all_src.append(r["pts_src_orig"])
            all_ref.append(r["pts_ref_orig"])
    if not all_src:
        return np.empty((0, 2)), np.empty((0, 2)), 0
    src = np.vstack(all_src)
    ref = np.vstack(all_ref)
    total_local = len(src)

    # Greedy dedup: keep the first occurrence, remove neighbours within radius
    keep = np.ones(len(src), dtype=bool)
    for i in range(len(src)):
        if not keep[i]:
            continue
        dists = np.linalg.norm(src[i + 1:] - src[i], axis=1)
        too_close = np.where(dists < radius)[0] + i + 1
        keep[too_close] = False

    src_unique = src[keep]
    ref_unique = ref[keep]
    n_removed = total_local - len(src_unique)

    return src_unique, ref_unique, n_removed


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("PIECEWISE AFFINE REGISTRATION PROTOTYPE")
    print("=" * 70)

    # Load imagery
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

    sx = SCALE_X_LRO_TO_OHRC   # ~10.5
    sy = SCALE_Y_LRO_TO_OHRC   # ~4.55

    # Scale OHRC to roughly match LRO resolution
    target_w = int(round(ohrc_norm.shape[1] / sx))
    target_h = int(round(ohrc_norm.shape[0] / sy))
    ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)

    h_src, w_src = ohrc_scaled.shape
    h_ref, w_ref = lro_norm.shape

    print(f"OHRC original: {ohrc_norm.shape}, scaled: {ohrc_scaled.shape}")
    print(f"LRO crop:      {lro_norm.shape}")

    # ── Step 2: Run 12-chunk local matching ──────────────────────────────────
    n_chunks = 12
    overlap_src = int(h_src * 0.2 / n_chunks) * 5
    overlap_ref = int(h_ref * 0.2 / n_chunks) * 5
    step_src = (h_src - overlap_src) // n_chunks
    step_ref = (h_ref - overlap_ref) // n_chunks

    matcher = EnsembleMatcher([
        LightGlueFeatureMatcher(max_dim=1500, max_keypoints=2048),
        RIFT2Matcher(),
    ])

    results = []
    for i in range(n_chunks):
        y1_src = i * step_src
        y2_src = y1_src + step_src + overlap_src if i < n_chunks - 1 else h_src
        y1_ref = i * step_ref
        y2_ref = y1_ref + step_ref + overlap_ref if i < n_chunks - 1 else h_ref

        res = run_chunk(matcher, ohrc_scaled, lro_norm,
                        y1_src, y2_src, y1_ref, y2_ref,
                        chunk_id=i + 1, sx=sx, sy=sy)
        results.append(res)

        flag = "✓" if res["status"] == "ACCEPTED" else "✗"
        print(f"  Chunk {i+1:02d} [{flag}]  raw={res['raw_matches']:3d}  "
              f"inliers={res['inliers']:2d}  RMSE={res['rmse']:.2f}  "
              f"det={res['det']:.4f}  "
              f"{'  ' + res['reason'] if res['status'] == 'REJECTED' else ''}")

    accepted = [r for r in results if r["status"] == "ACCEPTED"]
    rejected = [r for r in results if r["status"] == "REJECTED"]
    print(f"\nAccepted: {len(accepted)} / {n_chunks}")
    print(f"Rejected: {len(rejected)} / {n_chunks}")

    if not accepted:
        print("No accepted chunks. Cannot proceed with piecewise warp.")
        return

    # ── Step 2 cont'd: Piecewise affine warp ─────────────────────────────────
    print("\n--- Piecewise Affine Warp ---")
    pw_result = piecewise_affine_warp(ohrc_norm, lro_norm, results, sx, sy)
    if pw_result is None:
        return
    pw_img, pw_mask = pw_result

    cv2.imwrite(str(FIGURES_DIR / "ohrc_piecewise_affine.png"), pw_img)
    print(f"  Saved: {FIGURES_DIR / 'ohrc_piecewise_affine.png'}")

    # Overlay
    overlap_mask = pw_mask & (lro_norm > 0)
    overlay = np.zeros((*lro_norm.shape, 3), dtype=np.uint8)
    lro_bgr = cv2.cvtColor(lro_norm, cv2.COLOR_GRAY2BGR)
    pw_bgr = cv2.cvtColor(pw_img, cv2.COLOR_GRAY2BGR)
    overlay[lro_norm > 0] = lro_bgr[lro_norm > 0]
    overlay[pw_mask] = pw_bgr[pw_mask]
    overlay[overlap_mask] = (lro_bgr[overlap_mask] // 2) + (pw_bgr[overlap_mask] // 2)
    cv2.imwrite(str(FIGURES_DIR / "ohrc_piecewise_overlay.png"), overlay)
    print(f"  Saved: {FIGURES_DIR / 'ohrc_piecewise_overlay.png'}")

    # Checkerboard
    checker = np.zeros_like(lro_norm)
    y, x = np.mgrid[0:lro_norm.shape[0], 0:lro_norm.shape[1]]
    cell_mask = ((x // 50) + (y // 50)) % 2 == 0
    checker[lro_norm > 0] = lro_norm[lro_norm > 0]
    checker[pw_mask] = pw_img[pw_mask]
    checker[overlap_mask & cell_mask] = lro_norm[overlap_mask & cell_mask]
    checker[overlap_mask & ~cell_mask] = pw_img[overlap_mask & ~cell_mask]
    cv2.imwrite(str(FIGURES_DIR / "ohrc_piecewise_checkerboard.png"), checker)
    print(f"  Saved: {FIGURES_DIR / 'ohrc_piecewise_checkerboard.png'}")

    overlap_area = int(overlap_mask.sum())
    pw_valid = int(pw_mask.sum())
    overlap_pct = 100.0 * overlap_area / max(1, pw_valid)
    print(f"  Piecewise valid pixels: {pw_valid}  overlap with LRO: {overlap_area} ({overlap_pct:.1f}%)")

    # ── Step 3: Global affine for comparison ─────────────────────────────────
    print("\n--- Global Affine Comparison ---")
    all_src_pts = np.vstack([r["pts_src_orig"] for r in accepted])
    all_ref_pts = np.vstack([r["pts_ref_orig"] for r in accepted])

    M_global, mask_global = cv2.estimateAffine2D(
        all_src_pts, all_ref_pts, method=cv2.RANSAC, ransacReprojThreshold=15.0
    )
    if M_global is not None:
        global_warped = cv2.warpAffine(ohrc_norm, M_global, (w_ref, h_ref),
                                       flags=cv2.INTER_CUBIC,
                                       borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        global_mask = global_warped > 0
        cv2.imwrite(str(FIGURES_DIR / "ohrc_global_affine.png"), global_warped)
        global_valid = int(global_mask.sum())
        global_overlap = int((global_mask & (lro_norm > 0)).sum())
        print(f"  Global affine valid pixels: {global_valid}  "
              f"overlap: {global_overlap} ({100.0 * global_overlap / max(1, global_valid):.1f}%)")
    else:
        print("  Global affine estimation failed.")

    # ── Step 4: Residual consistency ─────────────────────────────────────────
    print("\n--- Residual Consistency (per-chunk RMSE) ---")
    print(f"  {'Chunk':>5} | {'Inliers':>7} | {'RMSE':>10}")
    print(f"  {'-'*5} | {'-'*7} | {'-'*10}")
    for r in results:
        if r["status"] == "ACCEPTED":
            print(f"  {r['chunk_id']:5d} | {r['inliers']:7d} | {r['rmse']:10.2f} px")

    neighbor_consistency(results, sy)

    # ── Step 5: Deduplicate control points ───────────────────────────────────
    print("\n--- Deduplicated Control Points ---")
    src_unique, ref_unique, n_removed = deduplicate_control_points(results, ohrc_norm.shape)
    total_local = sum(r["inliers"] for r in accepted)
    n_unique = len(src_unique)
    print(f"  Total local inliers:  {total_local}")
    print(f"  Removed as duplicates: {n_removed}")
    print(f"  Final unique points:  {n_unique}")

    if n_unique > 0:
        h_orig, w_orig = ohrc_norm.shape
        min_y = np.min(src_unique[:, 1])
        max_y = np.max(src_unique[:, 1])
        min_x = np.min(src_unique[:, 0])
        max_x = np.max(src_unique[:, 0])
        box_area = (max_x - min_x) * (max_y - min_y)
        coverage_pct = 100.0 * box_area / (h_orig * w_orig)

        bins_y = np.linspace(0, h_orig, 5)
        bins_x = np.linspace(0, w_orig, 5)
        grid_counts, _, _ = np.histogram2d(src_unique[:, 1], src_unique[:, 0],
                                           bins=[bins_y, bins_x])
        occupied = int(np.count_nonzero(grid_counts))

        print(f"  X range: [{min_x:.0f}, {max_x:.0f}]")
        print(f"  Y range: [{min_y:.0f}, {max_y:.0f}]")
        print(f"  Bounding-box coverage: {coverage_pct:.1f}%")
        print(f"  Grid cells occupied: {occupied}/16")
        print(f"  Grid cell counts:\n{grid_counts.astype(int)}")

        # Save CSV
        csv_path = SUBMISSION_DIR / "control_points_deduplicated.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ohrc_x", "ohrc_y", "lro_x", "lro_y"])
            for s, r in zip(src_unique, ref_unique):
                writer.writerow([f"{s[0]:.2f}", f"{s[1]:.2f}", f"{r[0]:.2f}", f"{r[1]:.2f}"])
        print(f"  Saved: {csv_path}")

        # Save plot
        plt.figure(figsize=(6, 12))
        plt.scatter(src_unique[:, 0], src_unique[:, 1], c='red', s=8, zorder=5)
        plt.xlim(0, w_orig)
        plt.ylim(h_orig, 0)
        plt.title(f"Deduplicated Control Points ({n_unique} pts)")
        plt.xlabel("OHRC X")
        plt.ylabel("OHRC Y")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(str(FIGURES_DIR / "control_points_deduplicated.png"), dpi=150)
        plt.close()
        print(f"  Saved: {FIGURES_DIR / 'control_points_deduplicated.png'}")

    # ── Step 6: TPS justification assessment ─────────────────────────────────
    print("\n--- TPS Justification Assessment ---")
    if n_unique >= 15 and occupied >= 4:
        print("  ✓ Sufficient unique control points for TPS.")
    else:
        print(f"  ✗ Only {n_unique} unique points in {occupied}/16 grid cells — "
              f"TPS would likely overfit.")

    # Check smoothness via neighbor diffs
    smooth = True
    for i in range(len(accepted) - 1):
        a, b = accepted[i], accepted[i + 1]
        # Quick check: do scales differ by > 50% between neighbors?
        if abs(a["sx_aff"] - b["sx_aff"]) / max(a["sx_aff"], b["sx_aff"], 1e-9) > 0.5:
            smooth = False
        if abs(a["sy_aff"] - b["sy_aff"]) / max(a["sy_aff"], b["sy_aff"], 1e-9) > 0.5:
            smooth = False

    if smooth:
        print("  ✓ Neighboring transforms have reasonably smooth parameter variation.")
    else:
        print("  ✗ Neighboring transforms show large jumps — TPS may overfit.")

    # ── Summary table ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"  Accepted chunks:    {len(accepted)} / {n_chunks}")
    print(f"  Rejected chunks:    {len(rejected)} / {n_chunks}")
    print(f"  Total raw matches:  {sum(r['raw_matches'] for r in results)}")
    print(f"  Total inliers:      {total_local}")
    print(f"  Unique ctrl pts:    {n_unique}")
    if n_unique > 0:
        print(f"  Coverage:           {coverage_pct:.1f}% ({occupied}/16 grid)")


if __name__ == "__main__":
    main()
