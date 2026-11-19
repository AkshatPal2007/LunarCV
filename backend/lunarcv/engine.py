"""One bounded, auditable registration pipeline shared by CLI and API.

All exported matrices map native source pixels to native reference pixels.
Fit diagnostics NEVER establish independent registration accuracy.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import tempfile
import time
import warnings
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import rasterio
import torch
from rasterio.errors import NotGeoreferencedWarning
from scipy.spatial import cKDTree
from skimage.transform import estimate_transform

from lunarcv.evaluation.manifest import sha256_file
from lunarcv.io.products import normalize_product, read_product
from lunarcv.matching.cache import cache_key, load_matches, save_matches
from lunarcv.registration.coordinates import PixelFrame, project_points
from lunarcv.registration.outlier_rejection import magsac_filter
from lunarcv.registration.spatial_uniformity import convex_hull_coverage, grid_occupancy
from lunarcv.registration.subpixel import refine_matches
from lunarcv.registration.transform import make_checkerboard, make_overlay
from lunarcv.settings import RegistrationConfig

ENGINE_VERSION = "0.3.0"


@dataclass
class RegistrationRun:
    metrics: dict
    transform: dict
    output_dir: Path


@lru_cache(maxsize=1)
def _matcher(kind, max_dim, max_keypoints, features):
    from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher

    if kind == "rift2":
        from lunarcv.matching.rift2_matcher import RIFT2Matcher

        return RIFT2Matcher(n_jobs=2)
    primary = LightGlueFeatureMatcher(
        max_dim=max_dim, max_keypoints=max_keypoints, features=features
    )
    if kind == "lightglue":
        return primary
    from lunarcv.matching.ensemble import EnsembleMatcher

    try:
        from lunarcv.matching.rift2_matcher import RIFT2Matcher

        secondary = RIFT2Matcher(n_jobs=2)
    except ImportError as exc:
        warnings.warn(
            f"RIFT2 unavailable; recording LightGlue-only fallback: {exc}", stacklevel=2
        )
        return EnsembleMatcher([primary])
    return EnsembleMatcher([primary, secondary])


def fit_transform(source, reference, model):
    """Single unweighted final fit on selected points; no residual cherry-picking."""
    source, reference = np.asarray(source), np.asarray(reference)
    required = 4 if model == "homography" else 3
    if len(source) < required or source.shape != reference.shape:
        raise ValueError("Insufficient paired points for final model")
    for points in (source, reference):
        if (
            not np.isfinite(points).all()
            or np.linalg.matrix_rank(points - points.mean(axis=0)) < 2
        ):
            raise ValueError("Non-finite or collinear control points")
    if model == "homography":
        matrix, _ = cv2.findHomography(source, reference, method=0)
    else:
        matrix = estimate_transform(model, source, reference).params
    if (
        matrix is None
        or not np.isfinite(matrix).all()
        or abs(np.linalg.det(matrix)) < 1e-10
    ):
        raise ValueError("Singular/non-finite final transform")
    return matrix


def _deduplicate(source, reference, scores, radius=1.5):
    if len(source) == 0:
        return source, reference, scores
    trees = cKDTree(source), cKDTree(reference)
    available = np.ones(len(source), dtype=bool)
    kept = []
    for i in np.argsort(-scores, kind="stable"):
        if not available[i]:
            continue
        kept.append(i)
        available[trees[0].query_ball_point(source[i], radius)] = False
        available[trees[1].query_ball_point(reference[i], radius)] = False
    return source[kept], reference[kept], scores[kept]


def _select(source, scores, shape, config):
    cells = {}
    height, width = shape
    for i, (x, y) in enumerate(source):
        cell = (
            min(config.grid_rows - 1, int(y * config.grid_rows / height)),
            min(config.grid_cols - 1, int(x * config.grid_cols / width)),
        )
        cells.setdefault(cell, []).append(i)
    return np.array(
        [
            i
            for indices in cells.values()
            for i in sorted(indices, key=lambda j: -scores[j])[: config.top_k]
        ],
        dtype=int,
    )


def _guided_matches(matcher, source, reference, config, heartbeat=None):
    def match(a, b):
        if heartbeat:
            heartbeat()
        result = matcher.match(a, b, conf_threshold=0.0)
        if any(not np.isfinite(v).all() for v in result):
            raise ValueError("Matcher returned non-finite values")
        return result

    initial = match(source, reference)
    diagnostics = {"full_scene": getattr(matcher, "diagnostics", {}), "guided_tiles": 0}
    if len(initial[0]) < 8 or config.tile_budget == 0:
        return (*_deduplicate(*initial), diagnostics)
    clean_s, _, _, prior, mask = magsac_filter(
        *initial,
        model="homography",
        ransac_reproj_threshold=config.reprojection_threshold,
    )
    if prior is None or len(clean_s) < 8:
        return (*_deduplicate(*initial), diagnostics)
    # Guidance only. This coarse homography is never the final exported model.
    height, width = source.shape
    src_parts, ref_parts, score_parts = [initial[0]], [initial[1]], [initial[2]]
    stride = max(64, config.tile_size - 96)
    tiles = [
        (x, y)
        for y in range(0, height, stride)
        for x in range(0, width, stride)
        if min(width - x, height - y) >= 96
    ]
    if len(tiles) > config.tile_budget:
        tiles = [
            tiles[i]
            for i in np.linspace(0, len(tiles) - 1, config.tile_budget, dtype=int)
        ]
    for x, y in tiles:
        x2, y2 = min(width, x + config.tile_size), min(height, y + config.tile_size)
        corners = project_points(prior, np.array([[x, y], [x2, y], [x2, y2], [x, y2]]))
        rx, ry = np.maximum(0, np.floor(corners.min(axis=0) - 64)).astype(int)
        rx2, ry2 = np.minimum(
            reference.shape[::-1], np.ceil(corners.max(axis=0) + 64)
        ).astype(int)
        if min(rx2 - rx, ry2 - ry) < 64:
            continue
        a, b, c = match(source[y:y2, x:x2], reference[ry:ry2, rx:rx2])
        src_parts.append(a + [x, y])
        ref_parts.append(b + [rx, ry])
        score_parts.append(c)
        diagnostics["guided_tiles"] += 1
    diagnostics["last_tile_matchers"] = getattr(matcher, "diagnostics", {})
    return (
        *_deduplicate(
            np.vstack(src_parts), np.vstack(ref_parts), np.concatenate(score_parts)
        ),
        diagnostics,
    )


def _coverage(points, shape, config):
    counts = grid_occupancy(points, *shape, config.grid_rows, config.grid_cols)
    histogram = counts["grid_counts"]
    return {
        "domain": "entire processing window; includes empty cells",
        "grid": [config.grid_rows, config.grid_cols],
        "grid_counts": histogram.tolist(),
        "occupancy_pct": counts["occupancy_pct"],
        "cv": float(histogram.std() / histogram.mean()) if histogram.mean() else None,
        "hull_coverage_pct": convex_hull_coverage(points, *shape),
    }


def _identity(features, matcher_kind):
    code_root = Path(__file__).parent
    digest = hashlib.sha256()
    for path in sorted(code_root.rglob("*.py")):
        digest.update(path.relative_to(code_root).as_posix().encode())
        digest.update(path.read_bytes())
    asset_manifest = code_root / "model_assets.json"
    digest.update(asset_manifest.read_bytes())
    expected = (
        json.loads(asset_manifest.read_text())[features]
        if matcher_kind != "rift2"
        else {}
    )
    weights = {}
    for name, checksum in expected.items():
        path = Path(torch.hub.get_dir(), "checkpoints", name)
        measured = sha256_file(path)
        if measured != checksum:
            raise ValueError(
                f"Pretrained weight checksum differs from pinned release asset: {name}"
            )
        weights[name] = measured
    return {
        "engine": ENGINE_VERSION,
        "code_sha256": digest.hexdigest(),
        "weights_sha256": weights,
        "torch": torch.__version__,
        "opencv": cv2.__version__,
        "lightglue": importlib.metadata.version("lightglue"),
    }


def _atomic_json(path, payload):
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".json")
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, indent=2, allow_nan=False)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class RegistrationEngine:
    def __init__(self, config=None):
        self.config = config or RegistrationConfig()

    def run(
        self,
        source_path,
        reference_path,
        output_dir,
        *,
        source_bounds=None,
        reference_bounds=None,
        source_scale_xy=(1.0, 1.0),
        cache_dir=None,
        reuse_cache=True,
        progress=None,
        controls_path=None,
        pair_metadata=None,
        prior_description="explicit input windows; geographic accuracy unverified",
    ):
        cfg = self.config
        started = time.perf_counter()
        timings = {}
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if (output_dir / "metrics.json").exists():
            raise FileExistsError(
                "Run output already exists; use a new output directory"
            )

        def mark(stage):
            nonlocal stage_start
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            timings[stage] = round(time.perf_counter() - stage_start, 6)
            stage_start = time.perf_counter()

        def update(percent, message):
            if progress:
                progress(percent, message)

        stage_start = time.perf_counter()
        cv2.setRNGSeed(cfg.seed)
        update(5, "Reading bounded image windows")
        if source_bounds is None and reference_bounds is None:
            from lunarcv.geo.raster_prior import overlap_windows

            geographic_prior = overlap_windows(source_path, reference_path)
            if geographic_prior:
                source_bounds = geographic_prior["source_bounds"]
                reference_bounds = geographic_prior["reference_bounds"]
                if tuple(source_scale_xy) == (1.0, 1.0):
                    source_scale_xy = geographic_prior["source_scale_xy"]
                prior_description = geographic_prior["description"]
        src = read_product(source_path, source_bounds, cfg.max_pixels)
        ref = read_product(reference_path, reference_bounds, cfg.max_pixels)
        sx, sy = source_scale_xy
        if not np.isfinite([sx, sy]).all() or min(sx, sy) <= 0:
            raise ValueError("Source GSD scale divisors must be positive and finite")
        src_u8, ref_u8 = normalize_product(src), normalize_product(ref)
        size = (
            max(16, round(src.data.shape[1] / sx)),
            max(16, round(src.data.shape[0] / sy)),
        )
        if size[0] * size[1] > cfg.max_pixels:
            raise ValueError("Scale-aligned image exceeds memory budget")
        source = cv2.resize(src_u8, size, interpolation=cv2.INTER_AREA)
        source_valid = (
            cv2.resize(
                src.valid.astype(np.uint8), size, interpolation=cv2.INTER_NEAREST
            )
            > 0
        )
        source_frame = PixelFrame(
            src.bounds[:2], (src.data.shape[1] / size[0], src.data.shape[0] / size[1])
        )
        reference_frame = ref.frame
        mark("load_normalize_scale")
        update(15, "Loading reusable pretrained matchers")
        matcher = _matcher(cfg.matcher, cfg.max_dim, cfg.max_keypoints, cfg.features)
        if hasattr(matcher, "reset_run"):
            matcher.reset_run()
        models = _identity(cfg.features, cfg.matcher)
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        mark("model_initialization")
        labels = {}
        for role, product in (("source", src), ("reference", ref)):
            sidecar = product.path.with_suffix(".xml")
            if sidecar.is_file():
                labels[role] = sha256_file(sidecar)
        identity = {
            "pair_metadata": pair_metadata or {"dataset_split": "unregistered"},
            "label_sha256": labels,
            "models": models,
            "config": cfg.model_dump(),
            "source_sha256": sha256_file(src.path),
            "reference_sha256": sha256_file(ref.path),
            "source_bounds": list(src.bounds),
            "reference_bounds": list(ref.bounds),
            "source_scale_xy": list(source_scale_xy),
        }
        mark("input_hashing")
        cache_path = (
            Path(cache_dir) / f"{cache_key(identity)}.npz" if cache_dir else None
        )
        cached = (
            load_matches(cache_path, identity) if cache_path and reuse_cache else None
        )
        update(25, "Matching full windows and geometry-guided tiles")
        if cached is None:
            source_pts, reference_pts, scores, diagnostics = _guided_matches(
                matcher, source, ref_u8, cfg, heartbeat=lambda: update(30,"Matching bounded tile")
            )
            # Discard invalid-data points before geometry, retaining true black pixels.
            keep = np.ones(len(source_pts), dtype=bool)
            for pts, valid in ((source_pts, source_valid), (reference_pts, ref.valid)):
                xy = np.rint(pts).astype(int)
                inside = (
                    (xy[:, 0] >= 0)
                    & (xy[:, 1] >= 0)
                    & (xy[:, 0] < valid.shape[1])
                    & (xy[:, 1] < valid.shape[0])
                )
                keep &= inside
                idx = np.flatnonzero(inside)
                keep[idx] &= valid[xy[idx, 1], xy[idx, 0]]
            source_pts, reference_pts, scores = (
                source_pts[keep],
                reference_pts[keep],
                scores[keep],
            )
            if cache_path:
                save_matches(
                    cache_path, identity, source_pts, reference_pts, scores, diagnostics
                )
        else:
            source_pts, reference_pts, scores, diagnostics = cached
        mark("matching_and_cache")
        candidate_count = len(source_pts)
        update(65, f"Geometric verification of {candidate_count} unique candidates")
        clean_s, clean_r, clean_c, _, inlier_mask = magsac_filter(
            source_pts,
            reference_pts,
            scores,
            model=cfg.model,
            ransac_reproj_threshold=cfg.reprojection_threshold,
        )
        if len(clean_s) < max(6, 4 if cfg.model == "homography" else 3):
            failure = {
                "schema_version": ENGINE_VERSION,
                "quality_decision": "REJECT",
                "reason": "insufficient geometric support",
                "candidate_matches": candidate_count,
                "magsac_inliers": len(clean_s),
                "evaluation_status": "not_validated",
                "evaluation": identity,
                "prior_description": prior_description,
                "stage_timings_s": timings,
                "execution_time_s": round(time.perf_counter() - started, 6),
                "matcher_diagnostics": diagnostics,
                "cache_hit": cached is not None,
                "subpixel_accuracy_claim": False,
            }
            np.savez_compressed(
                output_dir / "candidates.npz",
                source_native=project_points(source_frame.to_native, source_pts),
                reference_native=project_points(
                    reference_frame.to_native, reference_pts
                ),
                ranking_scores=scores,
                magsac_inlier=inlier_mask,
            )
            _atomic_json(output_dir / "metrics.json", failure)
            raise ValueError(
                f"Only {len(clean_s)} geometric inliers; rejection report saved"
            )
        selected = _select(clean_s, clean_c, source.shape, cfg)
        selected_s, selected_r, selected_c = (
            clean_s[selected],
            clean_r[selected],
            clean_c[selected],
        )
        provisional = fit_transform(selected_s, selected_r, cfg.model)
        mark("magsac_and_spatial_selection")
        update(75, "Conservative paired refinement before final fitting")
        refinement = {
            "method": "disabled",
            "accepted_mask": [False] * len(selected_s),
            "successfully_refined": 0,
        }
        refined_s = selected_s.copy()
        if cfg.refine:
            warped = cv2.warpPerspective(source, provisional, ref_u8.shape[::-1])
            warped_valid = (
                cv2.warpPerspective(
                    source_valid.astype(np.uint8),
                    provisional,
                    ref_u8.shape[::-1],
                    flags=cv2.INTER_NEAREST,
                )
                > 0
            )
            projected = project_points(provisional, selected_s).astype(np.float32)
            candidate, _, refinement = refine_matches(
                warped, ref_u8, projected, selected_r
            )
            # Border/nodata neighborhoods cannot establish correlation support.
            safe = cv2.erode(
                (warped_valid & ref.valid).astype(np.uint8), np.ones((23, 23), np.uint8)
            )
            accepted = np.asarray(refinement["accepted_mask"], bool)
            xy = np.rint(candidate).astype(int)
            inside = (
                (xy[:, 0] >= 0)
                & (xy[:, 1] >= 0)
                & (xy[:, 0] < safe.shape[1])
                & (xy[:, 1] < safe.shape[0])
            )
            accepted &= inside
            ix = np.flatnonzero(inside)
            accepted[ix] &= safe[xy[ix, 1], xy[ix, 0]] > 0
            refined_s[accepted] = project_points(
                np.linalg.inv(provisional), candidate[accepted]
            )
            refinement["accepted_mask"] = accepted.tolist()
            refinement["successfully_refined"] = int(accepted.sum())
            refinement["unrefinable_points"] = int((~accepted).sum())
        final = fit_transform(refined_s, selected_r, cfg.model)
        native = (
            reference_frame.to_native @ final @ np.linalg.inv(source_frame.to_native)
        )
        source_native = project_points(source_frame.to_native, refined_s)
        reference_native = project_points(reference_frame.to_native, selected_r)
        residuals = np.linalg.norm(
            project_points(native, source_native) - reference_native, axis=1
        )
        coverage_source = _coverage(refined_s, source.shape, cfg)
        coverage_reference = _coverage(selected_r, ref.data.shape, cfg)
        mark("refinement_and_final_fit")
        update(85, "Warping native radiometry into the reference window")
        crop_transform = (
            np.linalg.inv(ref.frame.to_native) @ native @ src.frame.to_native
        )
        size = ref.data.shape[::-1]
        science = cv2.warpPerspective(
            src.data, crop_transform, size, flags=cv2.INTER_LINEAR
        )
        valid = (
            cv2.warpPerspective(
                src.valid.astype(np.uint8),
                crop_transform,
                size,
                flags=cv2.INTER_NEAREST,
            )
            > 0
        )
        quicklook = cv2.warpPerspective(src_u8, crop_transform, size)
        overlap = valid & ref.valid
        overlap_pct = 100 * int(overlap.sum()) / max(1, int(ref.valid.sum()))
        mark("native_warp")
        rmse = float(np.sqrt(np.mean(residuals**2)))
        reasons = []
        if len(selected_s) < cfg.min_inliers:
            reasons.append("too few spatially selected inliers")
        if rmse > cfg.max_fit_rmse or not np.isfinite(rmse):
            reasons.append("excessive/non-finite fit residual")
        for label, coverage in (
            ("source", coverage_source),
            ("reference", coverage_reference),
        ):
            if coverage["occupancy_pct"] < cfg.min_occupancy_pct:
                reasons.append(f"poor {label} grid occupancy")
            if coverage["cv"] is None or coverage["cv"] > cfg.max_uniformity_cv:
                reasons.append(f"poor {label} spatial-uniformity CV")
            if coverage["hull_coverage_pct"] < cfg.min_hull_pct:
                reasons.append(f"poor {label} hull coverage")
        if overlap_pct < 5:
            reasons.append("insufficient overlap")
        independent = {
            "status": "unavailable",
            "rmse_reference_px": None,
            "reason": "no independent controls supplied",
        }
        if controls_path:
            from lunarcv.evaluation.controls import evaluate_controls

            independent = evaluate_controls(
                controls_path, native, source_native, reference_native
            )
        metrics = {
            "schema_version": ENGINE_VERSION,
            "candidate_matches": candidate_count,
            "magsac_inliers": int(inlier_mask.sum()),
            "inlier_matches": int(inlier_mask.sum()),
            "inlier_ratio": float(inlier_mask.mean()),
            "selected_matches": len(selected_s),
            "fit_reprojection_rmse_px": rmse,
            "fit_residual_median_px": float(np.median(residuals)),
            "fit_residual_p95_px": float(np.percentile(residuals, 95)),
            "residual_frame": "native reference pixels",
            "spatial_uniformity_cv": coverage_source["cv"],
            "coverage_source": coverage_source,
            "coverage_reference": coverage_reference,
            "overlap_pct": overlap_pct,
            "overlap_definition": "valid warped source intersect valid reference / valid reference window",
            "refinement": refinement,
            "independent_validation": independent,
            "subpixel_accuracy_claim": False,
            "evaluation_status": "independent_controls_scored"
            if controls_path
            else "fit_only_pending_independent_validation",
            "quality_decision": "REJECT"
            if reasons
            else "GEOMETRICALLY_USABLE_ACCURACY_UNVALIDATED",
            "quality_reasons": reasons,
            "matcher_diagnostics": diagnostics,
            "cache_hit": cached is not None,
            "stage_timings_s": timings,
            "prior_description": prior_description,
            "evaluation": identity,
            "hardware": {
                "platform": platform.platform(),
                "device": torch.cuda.get_device_name()
                if torch.cuda.is_available()
                else "cpu",
            },
            "warnings": [
                "Fit residuals are not independent accuracy.",
                "Processing-window coverage does not establish whole-scene coverage.",
                "Explicit crops are search windows, never ground truth.",
            ],
        }
        mapping = {
            "direction": "native_source_pixels_to_native_reference_pixels",
            "pixel_convention": "zero-based centers; x=column,y=row",
            "model": cfg.model,
            "matrix": native.tolist(),
            "inverse_matrix": np.linalg.inv(native).tolist(),
            "source_processing_to_native": source_frame.to_native.tolist(),
            "reference_processing_to_native": reference_frame.to_native.tolist(),
            "source_original_shape": list(src.original_shape),
            "reference_original_shape": list(ref.original_shape),
            "source_bounds_xyxy_exclusive": list(src.bounds),
            "reference_bounds_xyxy_exclusive": list(ref.bounds),
            "source_processing_shape": list(source.shape),
            "output_shape": list(ref.data.shape),
            "output_pixel_to_reference_native": ref.frame.to_native.tolist(),
            "georeferencing_status": "reference_crs_preserved"
            if ref.crs
            else "pixel_mapping_only_no_geographic_accuracy_claim",
        }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", NotGeoreferencedWarning)
            profile = {
                "driver": "GTiff",
                "height": size[1],
                "width": size[0],
                "count": 1,
                "dtype": science.dtype,
                "compress": "deflate",
            }
            if ref.crs:
                profile.update(crs=ref.crs, transform=ref.geotransform)
            with rasterio.open(
                output_dir / "registered.tif", "w", **profile
            ) as dataset:
                dataset.write(science, 1)
                dataset.write_mask(valid.astype(np.uint8) * 255)
        support_mask=np.zeros(ref_u8.shape,np.uint8)
        if len(selected_r)>=3:
            cv2.fillConvexPoly(support_mask,np.rint(cv2.convexHull(selected_r.astype(np.float32))).astype(np.int32),255)
        metrics["support_region_definition"]="Convex hull of fitted reference points; not an accuracy confidence map"
        images = {
            "support_mask.png":support_mask,
            "registered.png": quicklook,
            "valid_mask.png": valid.astype(np.uint8) * 255,
            "source.png": source,
            "reference.png": ref_u8,
            "overlay.png": make_overlay(quicklook, ref_u8, valid, ref.valid)[0],
            "checkerboard.png": make_checkerboard(
                quicklook, ref_u8, valid, ref.valid, overlap
            ),
        }
        # Diagnostic uses the same fitted points and pixel frames exported in CSV.
        match_canvas = np.zeros(
            (
                max(source.shape[0], ref_u8.shape[0]) + 36,
                source.shape[1] + ref_u8.shape[1],
                3,
            ),
            np.uint8,
        )
        match_canvas[36 : 36 + source.shape[0], : source.shape[1]] = cv2.cvtColor(
            source, cv2.COLOR_GRAY2BGR
        )
        match_canvas[36 : 36 + ref_u8.shape[0], source.shape[1] :] = cv2.cvtColor(
            ref_u8, cv2.COLOR_GRAY2BGR
        )
        for i, (a, b) in enumerate(zip(refined_s, selected_r, strict=True)):
            a = tuple(np.rint(a + [0, 36]).astype(int))
            b = tuple(np.rint(b + [source.shape[1], 36]).astype(int))
            cv2.line(match_canvas, a, b, (80, 180, 240), 1, cv2.LINE_AA)
            for point in (a, b):
                cv2.circle(match_canvas, point, 4, (60, 230, 100), 1, cv2.LINE_AA)
                cv2.putText(
                    match_canvas,
                    str(i + 1),
                    point,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35,
                    (0, 230, 255),
                    1,
                    cv2.LINE_AA,
                )
        cv2.putText(
            match_canvas,
            "REJECTED" if reasons else "ACCURACY UNVALIDATED",
            (8, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (50, 160, 255),
            1,
            cv2.LINE_AA,
        )
        images["matches.png"] = match_canvas
        for name, image in images.items():
            if not cv2.imwrite(str(output_dir / name), image):
                raise OSError(f"Could not write {name}")
        with (output_dir / "correspondence_points.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "point_id",
                    "source_x",
                    "source_y",
                    "reference_x",
                    "reference_y",
                    "primary_confidence",
                    "secondary_agreement",
                    "refined",
                    "fit_residual_reference_px",
                ]
            )
            for i, (a, b, score, error) in enumerate(
                zip(source_native, reference_native, selected_c, residuals, strict=True)
            ):
                writer.writerow(
                    [
                        i + 1,
                        *a,
                        *b,
                        float(score - 1) if score > 1 else float(score),
                        bool(cfg.matcher == "ensemble" and score > 1),
                        refinement["accepted_mask"][i],
                        error,
                    ]
                )
        # Preserve all candidate evidence; points outside selected set remain inspectable.
        np.savez_compressed(
            output_dir / "candidates.npz",
            source_native=project_points(source_frame.to_native, source_pts),
            reference_native=project_points(reference_frame.to_native, reference_pts),
            ranking_scores=scores,
            magsac_inlier=inlier_mask,
        )
        _atomic_json(output_dir / "transform.json", mapping)
        mark("write_products")
        metrics["execution_time_s"] = round(time.perf_counter() - started, 6)
        metrics["execution_time_scope"] = (
            "engine invocation; excludes interpreter/import startup"
        )
        metrics["peak_gpu_reserved_mb"] = (
            round(torch.cuda.max_memory_reserved() / 1024**2, 2)
            if torch.cuda.is_available()
            else None
        )
        metrics["peak_process_rss_mb"] = round(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2
        )
        metrics["peak_process_rss_scope"] = (
            "process lifetime including pretrained models"
        )
        metrics["peak_gpu_allocated_mb"] = (
            round(torch.cuda.max_memory_allocated() / 1024**2, 2)
            if torch.cuda.is_available()
            else None
        )
        _atomic_json(output_dir / "metrics.json", metrics)
        manifest = {
            "schema_version": ENGINE_VERSION,
            "status": "complete",
            "artifacts": {
                p.name: sha256_file(p) for p in output_dir.iterdir() if p.is_file()
            },
        }
        _atomic_json(output_dir / "manifest.json", manifest)
        update(100, f"Complete: {metrics['quality_decision']}")
        return RegistrationRun(metrics, mapping, output_dir)
