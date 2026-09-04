# Project Goals and Submission Plan

## What We Are Doing

LunarCV is a generic software pipeline for finding accurate, spatially distributed correspondence points between images captured by different lunar missions. The initial target is Chandrayaan-2 OHRC, TMC-2, and IIRS imagery matched with LRO NAC/WAC or SELENE imagery.

The pipeline must handle:

- Illumination changes caused by different Sun angles and shadow patterns.
- Viewpoint changes caused by different spacecraft and camera geometries.
- Scale changes caused by different GSDs, altitudes, and image resolutions.
- Large orbital image files without requiring the whole dataset to fit in RAM.

The project is a working hackathon solution. It prioritizes reliable composition of existing open-source pretrained models and measurable outputs over training a new model from scratch.

## What We Want to Achieve

1. Find high-confidence cross-mission matches automatically from real image files.
2. Reject false matches with robust geometry rather than visual confidence alone.
3. Spread the final matches across the scene so the transformation is not controlled by one small region.
4. Refine suitable points to sub-pixel precision and measure that claim independently.
5. Estimate a transformation that works for ordinary scenes and has a fallback for high-relief, terminator, or polar regions.
6. Produce a registered image that can be inspected visually and used by downstream lunar analysis.
7. Compare results against the published SuperGlue baseline while clearly labeling LunarCV's own measurements.

## Work Completed or Present in the Repository

The repository currently contains a baseline path for an OHRC to LRO NAC pair with:

- Real-image loading and memory-mapped access utilities.
- Overlap patch extraction.
- Percentile normalization and scale alignment.
- SuperPoint plus LightGlue feature matching.
- Chunked matching for larger patches.
- OpenCV MAGSAC++ homography filtering.
- Match arrays, homography output, figures, and baseline metric files.
- RIFT2 and sub-pixel refinement code that can support the next stages.

Existing processed files and metrics must always be traceable to the real input pair and configuration that produced them.

## Remaining Work Toward the Complete System

- Run LightGlue and RIFT2 as complementary paths on the same real pairs.
- Add agreement-based cross-validation and a documented LightGlue-only fallback.
- Add grid-based top-K selection after MAGSAC++.
- Apply sub-pixel refinement before the final transform fit.
- Add transform selection among similarity, affine, homography, and TPS.
- Add independent validation using real crater landmarks, metadata reprojection, or multi-sensor agreement.
- Evaluate equatorial and polar examples across the supported sensor pairs.
- Build a repeatable CLI workflow and an evaluation dashboard or report generator.
- Record timing and failure cases for every stage.

## Required Submission Package

### 1. Working software

Submit the runnable source code, dependency configuration, setup instructions, and an entry point that accepts real source/reference image paths. The entry point should document required metadata and output locations.

### 2. Registered output product

For each demonstrated pair, submit:

- The registered image product.
- The source and reference image identifiers.
- The final transformation parameters or matrix.
- The selected source/reference match points.
- A match overlay or side-by-side visualization.
- Any warnings about insufficient overlap, failed refinement, or fallback models.

### 3. Evaluation report

Report every test pair with:

- Candidate match count.
- MAGSAC++ inlier count.
- Inlier ratio.
- RMSE of inlier residuals.
- Spatial uniformity, using grid-tile coefficient of variation.
- Execution time for loading, preprocessing, matching, filtering, refinement, and warping.
- Independent registration error and its validation source, when available.
- Comparison with the published SuperGlue baseline.

### 4. Reproducibility and data provenance

Include the real data source, image identifiers, geographic footprint, GSD values, preprocessing settings, model names and versions, hardware, and command used for every reported result. Do not include fabricated ground truth or synthetic evaluation results.

## Definition of a Successful Demonstration

A successful demonstration runs end to end on a real Chandrayaan-2 and real LRO or SELENE pair, produces a visually aligned registered product and match-point file, survives geometric outlier rejection, reports spatial coverage and timing, and explains the limits of any accuracy claim. The result is successful only when its metrics and provenance can be independently inspected.
