"""Opt-in real-data smoke test of the isolated API worker. No synthetic evaluation."""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    directory = ROOT / "outputs/verification/api_worker_runs"
    os.environ["RESULTS_DIR"] = str(directory)
    os.environ["JOB_DB_PATH"] = str(directory / "jobs.sqlite3")
    from fastapi.testclient import TestClient

    from app.main import app

    pair = json.loads((ROOT / "data/metadata/demo_pair.json").read_text())
    request = {
        "source_image_id": Path(pair["source"]).stem,
        "reference_image_id": Path(pair["reference"]).stem,
        "source_bounds": pair["source_bounds"],
        "reference_bounds": pair["reference_bounds"],
        "source_scale_xy": pair["source_scale_xy"],
        "matcher": "lightglue",
        "features": "aliked",
        "model": "affine",
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/register", json=request)
        response.raise_for_status()
        job = response.json()["job_id"]
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            status = client.get(f"/api/v1/jobs/{job}").json()
            if status["status"] in ("completed", "failed", "cancelled"):
                break
            time.sleep(1)
        else:
            raise TimeoutError("API worker smoke test timed out")
        results = client.get(f"/api/v1/jobs/{job}/results")
        results.raise_for_status()
        payload = results.json()
        if payload["status"] != "completed":
            raise RuntimeError(payload)
        for key in (
            "transform_url",
            "science_raster_url",
            "metrics_url",
            "manifest_url",
        ):
            if client.get(payload[key]).status_code != 200:
                raise RuntimeError(f"Artifact retrieval failed: {key}")
        print(
            json.dumps(
                {
                    "job_id": job,
                    "status": payload["status"],
                    "quality": payload["metrics"]["quality_decision"],
                    "output_dir": str(directory / job),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
