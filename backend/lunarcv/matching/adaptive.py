import cv2
import numpy as np

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
        return 0, 0, 0.0, None, None, None, None

    pts_src, pts_ref, conf = matcher.match(patch_src, patch_ref, conf_threshold=0.0)
    n_raw = len(pts_src)

    if n_raw < 4:
        return n_raw, 0, 0.0, None, None, None, None

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
        return n_raw, 0, 0.0, None, None, None, None

    mask = raw_mask.ravel().astype(bool)
    n_in = int(mask.sum())

    rmse = 0.0
    if n_in > 0:
        hom = np.hstack([pts_src_orig[mask], np.ones((n_in, 1))])
        proj = (M @ hom.T).T
        rmse = float(np.sqrt(np.mean(np.sum((proj - pts_ref_g[mask]) ** 2, axis=1))))

    return n_raw, n_in, rmse, M, pts_src_orig[mask], pts_ref_g[mask], conf[mask]


def adaptive_chunked_match(
    matcher, ohrc_norm, lro_norm, sx_base, sy_base, n_chunks=12, overlap_frac=0.16, dedup_radius=20.0
):
    """
    Runs an adaptive scale search across chunks and returns deduplicated 
    (src_pts, ref_pts, conf) in ORIGINAL OHRC coordinates and LRO coordinates.
    """
    # Scale search grid
    sx_grid = [sx_base * 0.85, sx_base, sx_base * 1.15]           # ~[8.9, 10.5, 12.1]
    sy_grid = [sy_base * 0.75, sy_base * 0.88, sy_base,
               sy_base * 1.12, sy_base * 1.25]                    # ~[3.4, 4.0, 4.55, 5.1, 5.7]

    scale_combos = [(sxi, syi) for sxi in sx_grid for syi in sy_grid]

    chunk_step = 1.0 / n_chunks
    chunk_ranges = []
    for i in range(n_chunks):
        frac_start = max(0.0, i * chunk_step - overlap_frac / 2)
        frac_end = min(1.0, (i + 1) * chunk_step + overlap_frac / 2)
        chunk_ranges.append((frac_start, frac_end))

    best_results = []
    
    for ci, (frac_s, frac_e) in enumerate(chunk_ranges):
        best_in = 0
        best_raw = 0
        best_rmse = 999.0
        best_M = None
        best_src = None
        best_ref = None
        best_conf = None
        
        for sxi, syi in scale_combos:
            n_raw, n_in, rmse, M, src_pts, ref_pts, conf_pts = try_scale(
                matcher, ohrc_norm, lro_norm, (frac_s, frac_e), sxi, syi,
            )
            # Primary criterion: max inliers. Tiebreak: lower RMSE.
            if n_in > best_in or (n_in == best_in and n_in > 0 and rmse < best_rmse):
                best_in = n_in
                best_raw = n_raw
                best_rmse = rmse
                best_M = M
                best_src = src_pts
                best_ref = ref_pts
                best_conf = conf_pts
                
        status = "REJECTED"
        if best_M is not None:
            tx, ty, asx, asy, rot, det = decompose_affine(best_M)
            if is_degenerate(best_in, det, asx, asy, rot, best_rmse) is None:
                status = "ACCEPTED"
                
        if status == "ACCEPTED":
            best_results.append({
                "pts_src": best_src,
                "pts_ref": best_ref,
                "conf": best_conf,
                "raw": best_raw
            })

    if not best_results:
        return np.empty((0, 2), dtype=np.float32), np.empty((0, 2), dtype=np.float32), [], np.empty((0,), dtype=np.float32)

    all_src = np.vstack([r["pts_src"] for r in best_results])
    all_ref = np.vstack([r["pts_ref"] for r in best_results])
    all_conf = np.concatenate([r["conf"] for r in best_results])
    
    # Deduplicate
    keep = np.ones(len(all_src), dtype=bool)
    for i in range(len(all_src)):
        if not keep[i]:
            continue
        dists = np.linalg.norm(all_src[i + 1:] - all_src[i], axis=1)
        keep[np.where(dists < dedup_radius)[0] + i + 1] = False
        
    src_u = all_src[keep]
    ref_u = all_ref[keep]
    conf_u = all_conf[keep]
    
    return src_u, ref_u, best_results, conf_u
