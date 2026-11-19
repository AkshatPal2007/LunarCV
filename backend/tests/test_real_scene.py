"""Opt-in real-data regression. Never generates replacement imagery."""

import json
import os
from pathlib import Path

import numpy as np
import pytest


@pytest.mark.skipif(
    os.environ.get("LUNARCV_REAL_DATA") != "1",
    reason="Requires acquired real OHRC/LRO files and pretrained weights",
)
def test_real_scene_native_mapping_and_cache_reproducibility(tmp_path):
    from lunarcv.audit import inspect_run
    from lunarcv.engine import RegistrationEngine

    root = Path(__file__).resolve().parents[2]
    pair = json.loads((root / "data/metadata/demo_pair.json").read_text())
    paths = [root / pair[key] for key in ("source", "reference")]
    assert all(path.is_file() for path in paths), (
        "Acquire the mission images; no fixture fallback is permitted"
    )
    kwargs = {
        "source_bounds": pair["source_bounds"],
        "reference_bounds": pair["reference_bounds"],
        "source_scale_xy": pair["source_scale_xy"],
        "cache_dir": tmp_path / "cache",
    }
    engine = RegistrationEngine()
    fresh = engine.run(*paths, tmp_path / "fresh", reuse_cache=False, **kwargs)
    cached = engine.run(*paths, tmp_path / "cached", reuse_cache=True, **kwargs)
    assert cached.metrics["cache_hit"] is True
    np.testing.assert_array_equal(fresh.transform["matrix"], cached.transform["matrix"])
    assert (fresh.output_dir / "correspondence_points.csv").read_bytes() == (
        cached.output_dir / "correspondence_points.csv"
    ).read_bytes()
    assert fresh.metrics["subpixel_accuracy_claim"] is False
    assert fresh.metrics["independent_validation"]["status"] == "unavailable"
    assert inspect_run(fresh.output_dir)["artifacts_verified"]
