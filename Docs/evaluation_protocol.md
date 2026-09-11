# Frozen Evaluation Protocol

The canonical evaluation contract is [data/metadata/evaluation_manifest.json](../data/metadata/evaluation_manifest.json).

## Rules

- Evaluation pairs are split at the complete-scene level. Crops from one scene are not independent samples.
- The manifest is versioned and records sensor, product ID, image shape, GSD, footprint, and source paths.
- Every result records SHA-256 hashes of both input files, the matcher, parameters, protocol version, and dataset split.
- API uploads that are not explicitly registered in the manifest are labeled `unregistered` and must not be included in benchmark tables.
- A transform-fit residual is diagnostic only. It is not an accuracy claim.
- The pipeline deterministically holds out 20% of the raw correspondence set before MAGSAC++, fits a robust homography only on the remaining points, and scores only the held-out raw candidates.
- Held-out scoring requires at least 4 fit points and 2 held-out points. Smaller results are marked `insufficient_points_for_holdout` and cannot pass the quality gate.
- `independent_control_point_rmse_px` remains unavailable until a separate crater/control-point set is created.
- Ground-truth status is explicit. The current OHRC/LRO entry is `not_available`, so the project must not claim independently verified sub-pixel accuracy.

## Required Result Fields

```json
{
  "evaluation": {
    "manifest_version": "1.0",
    "protocol_version": "priority-0-v1",
    "pair_id": "...",
    "dataset_split": "test",
    "source": {"sha256": "...", "shape": [0, 0]},
    "reference": {"sha256": "...", "shape": [0, 0]},
    "matcher": "...",
    "parameters": {},
    "ground_truth": {"method": "...", "status": "..."}
  },
  "fit_reprojection_rmse_px": 0.0,
  "heldout_rmse_forward_px": 0.0,
  "heldout_rmse_backward_px": 0.0,
  "evaluation_status": "heldout_valid"
}
```

The current `fit_*` values are retained for debugging and regression tracking. They must not be compared with published independent RMSE values as if they measured the same thing.
