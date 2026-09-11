"""
Example: Using the object management system for a registration pipeline.

This shows how to use Pipeline and data models to manage intermediate outputs
and maintain clean boundaries between stages.
"""

from pathlib import Path

import numpy as np

from lunarcv.models import (
    EvaluationMetrics,
    LunarImage,
    MatchSet,
    Pipeline,
    TransformModel,
)


def run_registration_pipeline(source_path: Path, reference_path: Path):
    """End-to-end registration pipeline example"""

    # Initialize pipeline (tracks intermediate outputs in outputs/<name>/)
    pipeline = Pipeline("example_registration")

    # Stage 1: Load and normalize images
    print("Stage 1: Loading images...")
    source = LunarImage(
        path=source_path,
        data=np.random.rand(512, 512),  # placeholder
        sensor="OHRC",
        mission="Chandrayaan-2",
        gsd=0.25,
    )

    reference = LunarImage(
        path=reference_path,
        data=np.random.rand(512, 512),  # placeholder
        sensor="LRO_NAC",
        mission="LRO",
        gsd=0.5,
    )

    # Save normalized images
    stage_dir = pipeline.get_stage_dir("normalize")
    source.save(stage_dir / "source")
    reference.save(stage_dir / "reference")
    pipeline.record_stage("normalize", stage_dir, metadata={"gsd_ratio": 2.0})

    # Stage 2: Feature matching
    print("Stage 2: Matching features...")
    matches = MatchSet(
        source_name="source",
        reference_name="reference",
        source_kpts=np.random.rand(100, 2) * 512,
        reference_kpts=np.random.rand(100, 2) * 512,
        matcher_type="lightglue",
        confidence=np.random.rand(100),
    )

    stage_dir = pipeline.get_stage_dir("matching")
    matches.save(stage_dir)
    pipeline.record_stage(
        "matching", stage_dir, metadata={"n_matches": matches.n_matches}
    )

    # Stage 3: Registration
    print("Stage 3: Computing transform...")
    transform = TransformModel(
        transform_type="affine",
        matrix=np.eye(3),
        rmse=0.45,
    )

    stage_dir = pipeline.get_stage_dir("registration")
    transform.save(stage_dir, "transform")
    pipeline.record_stage("registration", stage_dir)

    # Stage 4: Evaluation
    print("Stage 4: Evaluating...")
    metrics = EvaluationMetrics(
        source_name="source",
        reference_name="reference",
        n_matches=100,
        n_inliers=87,
        inlier_ratio=0.87,
        rmse=0.45,
        mean_error=0.38,
        spatial_uniformity_cv=0.23,
        total_time=1.2,
    )

    stage_dir = pipeline.get_stage_dir("evaluation")
    metrics.save(stage_dir)
    pipeline.record_stage("evaluation", stage_dir)

    # Print summary
    print("\nPipeline summary:")
    print(f"  Output dir: {pipeline.output_dir}")
    print(f"  Completed stages: {', '.join(pipeline.summary()['completed_stages'])}")
    print(f"  RMSE: {metrics.rmse:.2f} pixels")
    print(f"  Inlier ratio: {metrics.inlier_ratio:.1%}")


if __name__ == "__main__":
    # Example paths (replace with real data paths)
    source = Path("data/raw/chandrayaan2_ohrc_example.tif")
    reference = Path("data/raw/lro_nac_example.tif")

    run_registration_pipeline(source, reference)
