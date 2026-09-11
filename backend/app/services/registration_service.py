"""
registration_service.py — Orchestrates the full LunarCV registration pipeline for API requests.

Pipeline (no hardcoded satellite-specific values):
  1. Load uploaded images (any grayscale-convertible format)
  2. Normalise (percentile stretch → uint8)
  3. Dynamic vertical-strip tiling based on actual image dimensions
  4. Per-strip: LightGlue (primary) + RIFT2 fallback if LightGlue is sparse
  5. Global MAGSAC++ outlier rejection on all candidates
  6. Spatially distributed top-K filter
  7. Sub-pixel cornerSubPix refinement
  8. Least-squares homography (cv2.findHomography method=0)
  9. Warp, overlay, checkerboard, CSV, metrics
 10. Quality gate (ACCEPT / REJECT)
"""

from __future__ import annotations

import csv
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from app.config import settings
from app.schemas.common import JobStatus
from app.services.image_loader import ImageLoadError, load_image_auto
from lunarcv.evaluation.manifest import EvaluationManifest, build_run_provenance
from lunarcv.evaluation.metrics import (
    RegistrationMetrics,
    calculate_rmse,
    evaluate_homography_holdout,
    evaluate_spatial_uniformity,
    quality_gate,
)
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.registration.outlier_rejection import magsac_filter
from lunarcv.registration.spatial_uniformity import spatial_topk_filter
from lunarcv.registration.subpixel import refine_matches
from lunarcv.registration.transform import (
    compute_registration,
    make_checkerboard,
    make_overlay,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional RIFT2
# ---------------------------------------------------------------------------
try:
    from lunarcv.matching.rift2_matcher import RIFT2Matcher

    _RIFT2_AVAILABLE = True
except ImportError:
    _RIFT2_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_gray(path: Path) -> np.ndarray:
    """
    Load an image as uint8 grayscale.
    Supports: PNG, JPEG, BMP, TIFF, or any OpenCV-readable format.
    Raises ValueError if the file cannot be read.
    """
    try:
        img, metadata = load_image_auto(
            path, max_dimension=settings.MAX_IMAGE_DIMENSION
        )
    except ImageLoadError as exc:
        raise ValueError(str(exc)) from exc
    if metadata["patch_extracted"]:
        raise ValueError(
            "Refusing to register an independently centre-cropped raw lunar image. "
            "Use the metadata-driven CLI geographic crop path for raw .IMG products."
        )
    return img


def _percentile_stretch(
    img: np.ndarray, p_low: float = 1.0, p_high: float = 99.0
) -> np.ndarray:
    """Robust percentile stretch to uint8 [0, 255]."""
    v_min, v_max = np.percentile(img, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0
    stretched = np.clip(
        (img.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255
    )
    return stretched.astype(np.uint8)


# ---------------------------------------------------------------------------
# Registration pipeline
# ---------------------------------------------------------------------------


def run_registration(
    job_id: str,
    source_path: Path,
    reference_path: Path,
    matcher: str,
    job_store: dict,
) -> None:
    """
    Run the registration pipeline in the background.
    Updates job_store with progress, status, and results.
    """
    import time

    t0 = time.time()

    def _update(progress: int, message: str) -> None:
        job_store[job_id]["progress"] = progress
        job_store[job_id]["message"] = message

    try:
        job_store[job_id]["status"] = JobStatus.PROCESSING
        _update(0, "Loading images…")

        # ── 1. Load & normalise ──────────────────────────────────────────────
        src_raw = _load_gray(source_path)
        ref_raw = _load_gray(reference_path)
        src_img = _percentile_stretch(src_raw)
        ref_img = _percentile_stretch(ref_raw)
        h_src, w_src = src_img.shape
        h_ref, w_ref = ref_img.shape

        evaluation_manifest = EvaluationManifest.load(settings.EVALUATION_MANIFEST_PATH)
        run_provenance = build_run_provenance(
            manifest=evaluation_manifest,
            source_path=source_path,
            reference_path=reference_path,
            source_shape=(h_src, w_src),
            reference_shape=(h_ref, w_ref),
            matcher=matcher,
            parameters={
                "normalization": "percentile_stretch",
                "percentile_range": [1.0, 99.0],
                "strip_height": "max(image_height) / 10 clamped to [256, 2048]",
                "strip_overlap": "max(64, strip_height / 8)",
                "magsac_model": "homography",
                "magsac_reprojection_threshold_px": 4.0,
                "spatial_grid": [4, 4],
                "spatial_top_k_per_cell": 3,
                "refinement": "cornerSubPix",
                "transform_fit": "least_squares_homography",
            },
        )

        results_dir = settings.RESULTS_DIR / job_id
        results_dir.mkdir(parents=True, exist_ok=True)

        _update(10, "Initialising matchers…")

        # ── 2. Build matcher(s) ──────────────────────────────────────────────
        lightglue = LightGlueFeatureMatcher(max_dim=1500, max_keypoints=2048)
        rift2: RIFT2Matcher | None = None
        if _RIFT2_AVAILABLE and matcher in ("rift2", "ensemble"):
            try:
                rift2 = RIFT2Matcher()
            except Exception as exc:
                logger.warning(f"RIFT2 init failed: {exc}")

        # ── 3. Dynamic vertical-strip tiling (no hardcoded lat/lon) ─────────
        # Strip height is chosen to be 1/10 the taller image height, clamped
        # to a sensible range [256, 2048] px.
        strip_height = int(np.clip(max(h_src, h_ref) / 10, 256, 2048))
        strip_overlap = max(64, strip_height // 8)
        stride = strip_height - strip_overlap
        rift2_threshold = 5  # only invoke RIFT2 if LightGlue finds < N matches

        # The two images are matched strip-by-strip proportionally.
        # lro_ratio = how many ref rows correspond to 1 src row.
        lro_ratio = h_ref / h_src

        n_strips = max(1, (h_src - strip_overlap + stride - 1) // stride)
        _update(15, f"Running {n_strips}-strip matching (strip_h={strip_height}px)…")

        all_pts_src, all_pts_ref, all_conf = [], [], []

        for i in range(n_strips):
            y1_s = i * stride
            y2_s = min(y1_s + strip_height, h_src)
            y1_r = int(round(y1_s * lro_ratio))
            y2_r = int(round(y2_s * lro_ratio))
            y1_r, y2_r = max(0, y1_r), min(h_ref, y2_r)

            patch_src = src_img[y1_s:y2_s, :]
            patch_ref = ref_img[y1_r:y2_r, :]
            if patch_src.shape[0] < 64 or patch_ref.shape[0] < 64:
                continue

            # LightGlue (primary)
            pts_s, pts_r, conf = lightglue.match(
                patch_src, patch_ref, conf_threshold=0.0
            )

            # RIFT2 fallback on sparse strips
            if rift2 is not None and len(pts_s) < rift2_threshold:
                try:
                    r_s, r_r, r_c = rift2.match(
                        patch_src, patch_ref, conf_threshold=0.0
                    )
                    if len(r_s) > 0:
                        pts_s = np.vstack([pts_s, r_s]) if len(pts_s) > 0 else r_s
                        pts_r = np.vstack([pts_r, r_r]) if len(pts_r) > 0 else r_r
                        conf = np.concatenate([conf, r_c]) if len(conf) > 0 else r_c
                except Exception as exc:
                    logger.debug(f"RIFT2 strip {i} failed: {exc}")

            if len(pts_s) > 0:
                pts_s[:, 1] += y1_s  # restore global Y
                pts_r[:, 1] += y1_r
                all_pts_src.append(pts_s)
                all_pts_ref.append(pts_r)
                all_conf.append(conf)

            # Report strip-level progress (15 → 60%)
            _update(15 + int(45 * (i + 1) / n_strips), f"Strip {i + 1}/{n_strips}…")

        if not all_pts_src:
            raise ValueError("No feature matches found across any image strip.")

        mkpts_src = np.vstack(all_pts_src)
        mkpts_ref = np.vstack(all_pts_ref)
        conf_all = np.concatenate(all_conf)
        holdout = evaluate_homography_holdout(
            mkpts_ref,
            mkpts_src,
            seed=evaluation_manifest.seed,
        )

        # ── 4. MAGSAC++ outlier rejection ────────────────────────────────────
        _update(62, f"MAGSAC++ on {len(mkpts_src)} candidates…")
        mkpts_src_c, mkpts_ref_c, conf_c, _, _ = magsac_filter(
            mkpts_src,
            mkpts_ref,
            conf_all,
            model="homography",
            ransac_reproj_threshold=4.0,
        )

        if len(mkpts_src_c) < 4:
            raise ValueError(
                f"Insufficient inliers after MAGSAC++ ({len(mkpts_src_c)})."
            )

        # ── 5. Spatial top-K ─────────────────────────────────────────────────
        mkpts_src_k, mkpts_ref_k, conf_k = spatial_topk_filter(
            mkpts_src_c,
            mkpts_ref_c,
            conf_c,
            h_src,
            w_src,
            n_rows=4,
            n_cols=4,
            top_k_per_cell=3,
        )

        # ── 6. Sub-pixel refinement ──────────────────────────────────────────
        _update(75, "Sub-pixel refinement…")
        mkpts_src_r, mkpts_ref_r, _ = refine_matches(
            src_img,
            ref_img,
            mkpts_src_k,
            mkpts_ref_k,
        )

        # ── 7. Homography (pure least-squares on MAGSAC++ inliers) ──────────
        _update(85, "Computing final transform…")
        reg = compute_registration(
            ref_img=ref_img,
            src_img=src_img,
            pts_ref=mkpts_ref_r,
            pts_src=mkpts_src_r,
        )
        if reg is None:
            raise ValueError("Failed to compute final homography.")

        # ── 8. Metrics ───────────────────────────────────────────────────────
        rmse_fwd, rmse_bwd = calculate_rmse(mkpts_ref_r, mkpts_src_r, reg.H)
        su = evaluate_spatial_uniformity(mkpts_ref_r, ref_img.shape, grid_size=(4, 4))
        inlier_ratio = len(mkpts_src_r) / max(1, len(conf_all))

        metrics_obj = RegistrationMetrics(
            candidate_matches=len(conf_all),
            inlier_matches=len(mkpts_src_r),
            inlier_ratio=inlier_ratio,
            rmse_forward=rmse_fwd,
            rmse_backward=rmse_bwd,
            spatial_uniformity=su,
            overlap_pct=reg.overlap_pct,
            execution_time_s=time.time() - t0,
            decision="",
            heldout_rmse_forward=holdout.rmse_forward,
            heldout_rmse_backward=holdout.rmse_backward,
            evaluation_status=holdout.status,
        )
        metrics_obj.decision = quality_gate(metrics_obj)

        # ── 9. Save outputs ──────────────────────────────────────────────────
        _update(95, "Generating output products…")

        cv2.imwrite(str(results_dir / "registered.png"), reg.warped_ref)

        overlay, _ = make_overlay(
            reg.warped_ref, reg.warped_src, reg.mask_ref, reg.mask_src
        )
        cv2.imwrite(str(results_dir / "overlay.png"), overlay)

        checker = make_checkerboard(
            reg.warped_ref,
            reg.warped_src,
            reg.mask_ref,
            reg.mask_src,
            reg.mask_overlap,
            grid_size=50,
        )
        cv2.imwrite(str(results_dir / "checkerboard.png"), checker)

        # Correspondence CSV
        csv_path = results_dir / "correspondence_points.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "source_x",
                    "source_y",
                    "reference_x",
                    "reference_y",
                    "confidence",
                    "inlier",
                ]
            )
            for p_s, p_r, c in zip(mkpts_src_r, mkpts_ref_r, conf_k, strict=True):
                w.writerow([p_s[0], p_s[1], p_r[0], p_r[1], float(c), 1])

        # Metrics JSON
        metrics_dict = {
            "evaluation": run_provenance,
            "candidate_matches": metrics_obj.candidate_matches,
            "inlier_matches": metrics_obj.inlier_matches,
            "inlier_ratio": metrics_obj.inlier_ratio,
            "fit_rmse_forward_px": metrics_obj.rmse_forward,
            "fit_rmse_backward_px": metrics_obj.rmse_backward,
            "heldout_rmse_forward_px": metrics_obj.heldout_rmse_forward,
            "heldout_rmse_backward_px": metrics_obj.heldout_rmse_backward,
            "evaluation_status": metrics_obj.evaluation_status,
            "holdout_fit_count": holdout.fit_count,
            "holdout_count": holdout.heldout_count,
            "spatial_uniformity_cv": metrics_obj.spatial_uniformity,
            "overlap_pct": metrics_obj.overlap_pct,
            "execution_time_s": metrics_obj.execution_time_s,
            "quality_decision": metrics_obj.decision,
        }
        with open(results_dir / "metrics.json", "w") as f:
            json.dump(metrics_dict, f, indent=4)

        # ── 10. Mark complete ─────────────────────────────────────────────────
        job_store[job_id]["status"] = JobStatus.COMPLETED
        job_store[job_id]["progress"] = 100
        job_store[job_id]["message"] = f"Registration complete — {metrics_obj.decision}"
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()
        job_store[job_id]["metrics"] = metrics_dict

    except Exception as exc:
        job_store[job_id]["status"] = JobStatus.FAILED
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()
        job_store[job_id]["error"] = str(exc)
        job_store[job_id]["message"] = f"Failed: {exc}"
        logger.error(f"Registration job {job_id} failed:\n{traceback.format_exc()}")
