"""lunarcv.evaluation — Registration metrics and quality gate."""
from lunarcv.evaluation.metrics import (
    HoldoutEvaluation,
    RegistrationMetrics,
    calculate_rmse,
    deterministic_holdout_split,
    evaluate_homography_holdout,
    evaluate_spatial_uniformity,
    quality_gate,
)
from lunarcv.evaluation.manifest import (
    EvaluationManifest,
    EvaluationPair,
    build_run_provenance,
    sha256_file,
)

__all__ = [
    "RegistrationMetrics",
    "HoldoutEvaluation",
    "calculate_rmse",
    "deterministic_holdout_split",
    "evaluate_homography_holdout",
    "evaluate_spatial_uniformity",
    "quality_gate",
    "EvaluationManifest",
    "EvaluationPair",
    "build_run_provenance",
    "sha256_file",
]
