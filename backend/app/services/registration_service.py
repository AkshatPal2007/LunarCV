"""
Registration service - orchestrates the CV pipeline for API requests.
"""

import json
import traceback
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np

from app.config import settings
from app.schemas.common import JobStatus
from lunarcv.io.raster import load_ohrc_memmap, load_lro_nac_memmap, extract_patch
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.registration.outlier_rejection import magsac_filter
from lunarcv.registration.spatial_uniformity import spatial_uniformity_report
from lunarcv.registration.subpixel import refine_matches
from lunarcv.registration.transform import compute_registration, make_overlay, make_checkerboard


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


async def run_registration(
    job_id: str,
    source_path: Path,
    reference_path: Path,
    matcher: str,
    job_store: dict
):
    """
    Run the registration pipeline in the background.

    Updates job_store with progress and results.
    """
    try:
        # Update status to processing
        job_store[job_id]["status"] = JobStatus.PROCESSING
        job_store[job_id]["progress"] = 0
        job_store[job_id]["message"] = "Loading images..."

        # Create results directory
        results_dir = settings.RESULTS_DIR / job_id
        results_dir.mkdir(parents=True, exist_ok=True)

        # Load images (simplified - assumes they're already normalized)
        # In production, you'd detect format and handle .IMG, .TIF, etc.
        source_img = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
        reference_img = cv2.imread(str(reference_path), cv2.IMREAD_GRAYSCALE)

        if source_img is None or reference_img is None:
            raise ValueError("Failed to load images")

        # Normalize
        job_store[job_id]["progress"] = 10
        job_store[job_id]["message"] = "Normalizing images..."

        source_norm = percentile_stretch_uint8(source_img)
        reference_norm = percentile_stretch_uint8(reference_img)

        # Feature matching
        job_store[job_id]["progress"] = 30
        job_store[job_id]["message"] = f"Running {matcher} feature matching..."

        if matcher == "lightglue":
            feature_matcher = LightGlueFeatureMatcher(max_dim=1500, max_keypoints=2048)
            mkpts_src, mkpts_ref, conf = feature_matcher.match(
                source_norm, reference_norm, conf_threshold=0.0
            )
        else:
            raise ValueError(f"Unsupported matcher: {matcher}")

        # Outlier rejection
        job_store[job_id]["progress"] = 60
        job_store[job_id]["message"] = "Running outlier rejection..."

        mkpts_src_clean, mkpts_ref_clean, conf_clean, H, mask = magsac_filter(
            mkpts_src, mkpts_ref, conf, model="homography", ransac_reproj_threshold=4.0
        )

        if H is None or len(mkpts_src_clean) < 4:
            raise ValueError("Insufficient inliers found")

        # Sub-pixel refinement
        job_store[job_id]["progress"] = 75
        job_store[job_id]["message"] = "Refining matches..."

        mkpts_src_ref, mkpts_ref_ref, stats = refine_matches(
            source_norm, reference_norm, mkpts_src_clean, mkpts_ref_clean
        )

        # Compute final registration
        job_store[job_id]["progress"] = 85
        job_store[job_id]["message"] = "Computing final transform..."

        reg = compute_registration(
            ref_img=reference_norm,
            src_img=source_norm,
            pts_ref=mkpts_ref_ref,
            pts_src=mkpts_src_ref,
        )

        if reg is None:
            raise ValueError("Failed to compute final registration")

        # Calculate metrics
        ref_3d = mkpts_ref_ref.astype(np.float32).reshape(-1, 1, 2)
        pred_src = cv2.perspectiveTransform(ref_3d, reg.H).reshape(-1, 2)
        residuals = np.linalg.norm(mkpts_src_ref - pred_src, axis=1)

        rmse = float(np.sqrt(np.mean(residuals**2)))
        median_err = float(np.median(residuals))
        max_err = float(np.max(residuals))
        inlier_ratio = len(mkpts_src_ref) / len(conf) if len(conf) > 0 else 0.0

        # Generate outputs
        job_store[job_id]["progress"] = 95
        job_store[job_id]["message"] = "Generating output products..."

        # Save registered image
        cv2.imwrite(str(results_dir / "registered.png"), reg.warped_ref)

        # Save overlay
        overlay, _ = make_overlay(
            reg.warped_ref, reg.warped_src, reg.mask_ref, reg.mask_src
        )
        cv2.imwrite(str(results_dir / "overlay.png"), overlay)

        # Save checkerboard
        checker = make_checkerboard(
            reg.warped_ref,
            reg.warped_src,
            reg.mask_ref,
            reg.mask_src,
            reg.mask_overlap,
            grid_size=50,
        )
        cv2.imwrite(str(results_dir / "checkerboard.png"), checker)

        # Save correspondence CSV
        import csv
        csv_path = results_dir / "correspondence_points.csv"
        with open(csv_path, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["source_x", "source_y", "reference_x", "reference_y"])
            for pt_s, pt_r in zip(mkpts_src_ref, mkpts_ref_ref, strict=True):
                writer.writerow([pt_s[0], pt_s[1], pt_r[0], pt_r[1]])

        # Save metrics
        h_src, w_src = source_norm.shape
        su_final = spatial_uniformity_report(
            mkpts_src_ref, h_src, w_src, label="Final", n_rows=4, n_cols=4
        )

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

        with open(results_dir / "metrics.json", "w") as f:
            json.dump(metrics, f, indent=4)

        # Mark complete
        job_store[job_id]["status"] = JobStatus.COMPLETED
        job_store[job_id]["progress"] = 100
        job_store[job_id]["message"] = "Registration complete"
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()
        job_store[job_id]["metrics"] = metrics

    except Exception as e:
        # Mark failed
        job_store[job_id]["status"] = JobStatus.FAILED
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()
        job_store[job_id]["error"] = str(e)
        job_store[job_id]["message"] = f"Failed: {str(e)}"

        # Log full traceback for debugging
        print(f"Registration job {job_id} failed:")
        print(traceback.format_exc())
