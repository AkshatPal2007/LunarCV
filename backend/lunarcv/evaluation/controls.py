"""Score external native-pixel controls AFTER registration; never fit to them."""

import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from lunarcv.evaluation.manifest import sha256_file
from lunarcv.registration.coordinates import project_points


def evaluate_controls(path, matrix, fit_source, fit_reference):
    payload = json.loads(Path(path).read_text())
    if (
        payload.get("coordinate_frame") != "native_pixels"
        or payload.get("independent_of_matching") is not True
    ):
        raise ValueError("Controls must declare independent native-pixel measurements")
    if not payload.get("method") or not payload.get("provenance"):
        raise ValueError("Control method and provenance are required")
    uncertainty = float(payload["uncertainty_reference_px"])
    if not np.isfinite(uncertainty) or uncertainty < 0:
        raise ValueError("Controls require finite nonnegative measurement uncertainty")
    source = np.array([p["source"] for p in payload["points"]], dtype=float)
    reference = np.array([p["reference"] for p in payload["points"]], dtype=float)
    if len(source) < 6 or source.shape != reference.shape:
        raise ValueError("At least six paired independent controls are required")
    prediction = project_points(matrix, source)
    if not np.isfinite(reference).all():
        raise ValueError("Non-finite control coordinates")
    for pts, fit in ((source, fit_source), (reference, fit_reference)):
        if np.any(cKDTree(fit).query(pts)[0] < 2):
            raise ValueError(
                "Controls overlap fitted match locations; provide unused independent features"
            )
    errors = np.linalg.norm(prediction - reference, axis=1)
    return {
        "status": "external_controls_scored_not_used_in_fit",
        "sha256": sha256_file(Path(path)),
        "method": payload["method"],
        "provenance": payload["provenance"],
        "count": len(source),
        "uncertainty_reference_px": uncertainty,
        "rmse_reference_px": float(np.sqrt(np.mean(errors**2))),
        "median_reference_px": float(np.median(errors)),
        "p95_reference_px": float(np.percentile(errors, 95)),
        "errors_reference_px": errors.tolist(),
    }
