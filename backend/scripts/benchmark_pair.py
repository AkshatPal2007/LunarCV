"""Benchmark real file registrations in separate processes; retain every run."""

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair", type=Path, default=ROOT / "data/metadata/demo_pair.json"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3, choices=range(1, 11))
    parser.add_argument("--mode", choices=["fresh", "cached"], default="fresh")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    rows = []
    for index in range(args.runs):
        target = (args.output_dir / f"run-{index + 1:02d}").resolve()
        command = [
            sys.executable,
            str(ROOT / "backend/scripts/register_pair.py"),
            "--pair",
            str(args.pair.resolve()),
            "--output-dir",
            str(target),
        ]
        if args.mode == "fresh":
            command.append("--force-rematch")
        started = time.perf_counter()
        with (args.output_dir / f"run-{index + 1:02d}.log").open("w") as log:
            # Fixed interpreter/script with literal argv; no shell expansion.
            subprocess.run(  # noqa: S603
                command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True
            )
        metrics = json.loads((target / "metrics.json").read_text())
        rows.append(
            {
                "run": str(target),
                "process_wall_s": round(time.perf_counter() - started, 6),
                **{
                    key: metrics[key]
                    for key in (
                        "execution_time_s",
                        "cache_hit",
                        "candidate_matches",
                        "magsac_inliers",
                        "fit_reprojection_rmse_px",
                        "quality_decision",
                        "peak_process_rss_mb",
                    )
                },
            }
        )
    values = [row["execution_time_s"] for row in rows]
    report = {
        "scope": "real development pair; engine seconds exclude interpreter/import startup; process wall includes it",
        "mode": args.mode,
        "runs": rows,
        "median_engine_s": statistics.median(values),
        "min_engine_s": min(values),
        "max_engine_s": max(values),
        "independent_accuracy": "unavailable unless independently supplied; fit residual is not accuracy",
    }
    (args.output_dir / "benchmark.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
