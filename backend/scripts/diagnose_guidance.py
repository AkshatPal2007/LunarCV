"""Isolated real-data development ablation; never writes the production cache.

Compare the fixed primary matcher with affine versus homography coarse guidance.
This is not independent accuracy validation and does not modify quality gates.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lunarcv.engine as engine
from lunarcv.evaluation.manifest import sha256_file

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair", type=Path, default=ROOT / "data/metadata/demo_pair.json"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--guidance-model", choices=["affine", "homography"], required=True
    )
    args = parser.parse_args()
    pair = json.loads(args.pair.read_text())
    original = engine.magsac_filter

    def guidance(*values, **kwargs):
        if kwargs.get("model") == "homography":
            kwargs["model"] = args.guidance_model
        return original(*values, **kwargs)

    engine.magsac_filter = guidance
    try:
        run = engine.RegistrationEngine(
            engine.RegistrationConfig(matcher="lightglue")
        ).run(
            ROOT / pair["source"],
            ROOT / pair["reference"],
            args.output_dir,
            source_bounds=pair["source_bounds"],
            reference_bounds=pair["reference_bounds"],
            source_scale_xy=pair["source_scale_xy"],
            cache_dir=None,
            reuse_cache=False,
            pair_metadata={
                "dataset_split": "development",
                "experimental_guidance_model": args.guidance_model,
                "pair_manifest_sha256": sha256_file(args.pair),
                "experiment_script_sha256": sha256_file(Path(__file__)),
            },
            prior_description=pair["prior_description"],
        )
        print(
            json.dumps(
                {
                    key: run.metrics[key]
                    for key in (
                        "candidate_matches",
                        "magsac_inliers",
                        "fit_reprojection_rmse_px",
                        "coverage_source",
                        "quality_decision",
                        "execution_time_s",
                    )
                },
                indent=2,
            )
        )
    finally:
        engine.magsac_filter = original


if __name__ == "__main__":
    main()
