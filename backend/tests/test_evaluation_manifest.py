import json
from pathlib import Path

from lunarcv.evaluation.manifest import (
    EvaluationManifest,
    build_run_provenance,
    sha256_file,
)
from lunarcv.evaluation.metrics import (
    deterministic_holdout_split,
    evaluate_homography_holdout,
)
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "evaluation_manifest.json"


def test_frozen_manifest_requires_scene_level_split():
    manifest = EvaluationManifest.load(MANIFEST_PATH)

    assert manifest.manifest_version == "1.0"
    assert manifest.protocol_version == "priority-0-v1"
    assert manifest.pair_split_unit == "scene"
    assert manifest.pair("ohrc-lro-nac-m1350459544re-baseline").split == "test"
    assert manifest.metrics["fit_metrics_are_not_accuracy"] is True


def test_provenance_hashes_inputs_and_marks_unregistered_pair(tmp_path):
    source = tmp_path / "source.bin"
    reference = tmp_path / "reference.bin"
    source.write_bytes(b"source image bytes")
    reference.write_bytes(b"reference image bytes")

    provenance = build_run_provenance(
        manifest=EvaluationManifest.load(MANIFEST_PATH),
        source_path=source,
        reference_path=reference,
        source_shape=(20, 30),
        reference_shape=(40, 50),
        matcher="lightglue",
        parameters={"seed": 20260910},
    )

    assert provenance["dataset_split"] == "unregistered"
    assert provenance["pair_id"] is None
    assert provenance["source"]["sha256"] == sha256_file(source)
    assert provenance["reference"]["sha256"] == sha256_file(reference)
    assert provenance["parameters"] == {"seed": 20260910}


def test_manifest_is_valid_json():
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert payload["pairs"][0]["ground_truth_status"] == "not_available"


def test_holdout_split_is_deterministic_and_disjoint():
    first = deterministic_holdout_split(20, seed=7)
    second = deterministic_holdout_split(20, seed=7)

    assert first is not None
    assert second is not None
    fit, heldout = first
    assert np.array_equal(fit, second[0])
    assert np.array_equal(heldout, second[1])
    assert not set(fit).intersection(set(heldout))
    assert len(fit) + len(heldout) == 20


def test_holdout_evaluation_is_not_fit_residual():
    pts_ref = np.array(
        [[0, 0], [10, 0], [20, 0], [0, 10], [10, 10], [20, 10], [0, 20], [10, 20], [20, 20], [30, 20]],
        dtype=np.float32,
    )
    pts_src = pts_ref + np.array([5.0, -3.0], dtype=np.float32)
    pts_src[-1] += np.array([4.0, 6.0], dtype=np.float32)

    result = evaluate_homography_holdout(pts_ref, pts_src, seed=3)

    assert result.status == "heldout_valid"
    assert result.fit_count == 8
    assert result.heldout_count == 2
    assert result.rmse_forward is not None
    assert result.rmse_forward > 0.0


def test_holdout_evaluation_rejects_tiny_point_sets():
    points = np.zeros((5, 2), dtype=np.float32)
    result = evaluate_homography_holdout(points, points)

    assert result.status == "insufficient_points_for_holdout"
    assert result.rmse_forward is None
