"""Verify a run manifest and recompute final residuals without fitting anything."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from lunarcv.evaluation.manifest import sha256_file
from lunarcv.registration.coordinates import project_points


def inspect_run(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, digest in manifest["artifacts"].items():
        if Path(name).name != name or sha256_file(directory / name) != digest:
            raise ValueError(f"Artifact identity mismatch: {name}")
    mapping = json.loads((directory / "transform.json").read_text())
    with (directory / "correspondence_points.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    source = np.array(
        [[float(row["source_x"]), float(row["source_y"])] for row in rows]
    )
    reference = np.array(
        [[float(row["reference_x"]), float(row["reference_y"])] for row in rows]
    )
    error = np.linalg.norm(
        project_points(np.array(mapping["matrix"]), source) - reference, axis=1
    )
    exported = np.array([float(row["fit_residual_reference_px"]) for row in rows])
    if not np.allclose(error, exported, atol=1e-6):
        raise ValueError("CSV residuals do not match the native transform")
    metrics = json.loads((directory / "metrics.json").read_text())
    measured = float(np.sqrt(np.mean(error**2)))
    if not np.isclose(measured, metrics["fit_reprojection_rmse_px"], atol=1e-6):
        raise ValueError("Metrics disagree with native mapping")
    return {
        "artifacts_verified": True,
        "direction": mapping["direction"],
        "points": len(rows),
        "recomputed_fit_rmse_reference_px": measured,
        "independent_accuracy": metrics["independent_validation"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    print(json.dumps(inspect_run(parser.parse_args().run), indent=2))


if __name__ == "__main__":
    main()
