"""Register real files with one shared engine; inspect transform.json for mappings."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from lunarcv.evaluation.manifest import sha256_file

_checkout = Path(__file__).resolve().parents[2]
ROOT = _checkout if (_checkout / "backend/pyproject.toml").is_file() else Path.cwd()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair",
        type=Path,
        help="Real product/window manifest; defaults to the development pair",
    )
    parser.add_argument("--source", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument(
        "--source-bounds", type=int, nargs=4, metavar=("X0", "Y0", "X1", "Y1")
    )
    parser.add_argument(
        "--reference-bounds", type=int, nargs=4, metavar=("X0", "Y0", "X1", "Y1")
    )
    parser.add_argument("--scale-x", type=float)
    parser.add_argument("--scale-y", type=float)
    parser.add_argument(
        "--config",
        type=Path,
        help="JSON RegistrationConfig, frozen before evaluating a pair",
    )
    parser.add_argument("--matcher", choices=["ensemble", "lightglue", "rift2"])
    parser.add_argument("--features", choices=["disk", "aliked", "sift"])
    parser.add_argument("--model", choices=["similarity", "affine", "homography"])
    parser.add_argument("--tile-budget", type=int)
    parser.add_argument("--no-refine", action="store_true")
    parser.add_argument("--force-rematch", action="store_true")
    parser.add_argument(
        "--reuse-match-cache", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--controls",
        type=Path,
        help="Independent native-pixel controls with provenance; never used for fitting",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT
        / "outputs"
        / "runs"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"),
    )
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    from lunarcv.engine import RegistrationConfig, RegistrationEngine

    if bool(args.source) != bool(args.reference):
        raise ValueError("Provide both --source and --reference")
    pair_path = args.pair or (
        ROOT / "data/metadata/demo_pair.json" if not args.source else None
    )
    pair = json.loads(pair_path.read_text()) if pair_path else {}

    def path(value):
        p = Path(value)
        return p if p.is_absolute() else ROOT / p

    source = args.source or path(pair["source"])
    reference = args.reference or path(pair["reference"])
    settings = json.loads(args.config.read_text()) if args.config else {}
    for key in ("matcher", "model", "tile_budget", "features"):
        value = getattr(args, key)
        if value is not None:
            settings[key] = value
    if args.no_refine:
        settings["refine"] = False
    scale = pair.get("source_scale_xy", [1.0, 1.0])
    scale = (args.scale_x or scale[0], args.scale_y or scale[1])
    metadata = {"dataset_split": "unregistered"}
    if pair_path:
        metadata = {
            "pair_manifest_sha256": sha256_file(pair_path),
            "pair_id": pair.get("pair_id"),
            "dataset_split": pair.get("dataset_split", "unregistered"),
        }
        if pair.get("source_geometry"):
            metadata["source_geometry_sha256"] = sha256_file(
                path(pair["source_geometry"])
            )
    engine = RegistrationEngine(RegistrationConfig(**settings))
    result = engine.run(
        source,
        reference,
        args.output_dir,
        source_bounds=tuple(args.source_bounds or pair["source_bounds"])
        if args.source_bounds or pair.get("source_bounds")
        else None,
        reference_bounds=tuple(args.reference_bounds or pair["reference_bounds"])
        if args.reference_bounds or pair.get("reference_bounds")
        else None,
        source_scale_xy=scale,
        cache_dir=ROOT / "outputs/match_cache",
        reuse_cache=not args.force_rematch,
        controls_path=args.controls,
        pair_metadata=metadata,
        prior_description=pair.get(
            "prior_description",
            "user-supplied file windows; geographic mapping not established",
        ),
        progress=lambda p, m: logging.info("%3d%% %s", p, m),
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "candidate_matches": result.metrics["candidate_matches"],
                "magsac_inliers": result.metrics["magsac_inliers"],
                "selected_matches": result.metrics["selected_matches"],
                "fit_rmse_reference_px": result.metrics["fit_reprojection_rmse_px"],
                "quality_decision": result.metrics["quality_decision"],
                "independent_validation": result.metrics["independent_validation"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
