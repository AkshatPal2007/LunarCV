# LunarCV Working Architecture

## Purpose

LunarCV registers real Chandrayaan-2 imagery against real LRO NAC/WAC or SELENE imagery. It searches for correspondence points that remain reliable when the two images differ in illumination, viewpoint, and scale.

The source image is the Chandrayaan-2 image being registered. The reference image is the LRO or SELENE image used as the target coordinate system.

## Sequence Flow

```text
Real source and reference image files
                |
                v
1. Load imagery and metadata
   - Read large raster files with memory mapping where possible
   - Record image shape, data type, GSD, footprint, and illumination metadata
                |
                v
2. Establish a coarse geographic prior
   - Identify the overlapping geographic region
   - Crop the reference image to the likely overlap
   - Estimate the scale ratio from the sensors' GSD values
                |
                v
3. Normalize and align image scale
   - Apply a robust percentile stretch to uint8
   - Resize the source toward the reference scale
   - Keep preprocessing minimal for the learned matcher
                |
                v
4. Extract and match visual features
   - Extract SuperPoint keypoints and descriptors
   - Match them with pretrained LightGlue
   - Process large patches in chunks when required by memory limits
   - Run RIFT2 as the complementary phase-congruency matcher
     when the secondary path is enabled
                |
                v
5. Cross-validate candidate matches
   - Prefer matches supported by both matchers
   - Retain a LightGlue-only fallback when RIFT2 cannot produce useful matches
                |
                v
6. Reject geometrically inconsistent matches
   - Fit a homography, affine, or other suitable model
   - Use OpenCV MAGSAC++ to classify inliers and outliers
   - Calculate candidate count and inlier ratio
                |
                v
7. Enforce spatial coverage
   - Divide the image into grid tiles
   - Limit the number of selected matches per tile
   - Measure the coefficient of variation across tile counts
                |
                v
8. Refine points to sub-pixel precision
   - Use local image structure checks
   - Apply cornerSubPix or Lucas-Kanade refinement
   - Keep points that cannot be refined, but record that limitation
                |
                v
9. Estimate the final transformation
   - Use similarity, affine, or homography for ordinary regions
   - Use a thin-plate spline fallback for strong relief or polar distortion
                |
                v
10. Produce registered outputs
    - Warp the source or reference into the selected coordinate system
    - Save the registered image and match-point arrays
    - Save match overlays and other visual quality checks
                |
                v
11. Evaluate and report
    - RMSE of inlier residuals
    - Inlier count and inlier ratio
    - Match count and per-stage execution time
    - Spatial uniformity
    - Independent registration error where a real check is available
```

## What Happens in the Current Baseline

The baseline script currently demonstrates the first part of this flow for the OHRC to LRO NAC pair. It loads large images, extracts an overlapping patch, applies percentile normalization, rescales the OHRC patch, runs SuperPoint plus LightGlue in chunks, applies MAGSAC++, computes reprojection statistics, and saves match arrays and figures.

RIFT2, grid-based spatial selection, and independent real-data validation are part of the complete target architecture. Their results must be added to the evaluation only after they have been run on the actual sensor imagery.

## Important Data Rule

Evaluation and demo results must use real Chandrayaan-2, LRO, or SELENE imagery. Synthetic arrays may be used for unit tests of isolated code logic, but synthetic or rendered data must never be mixed into reported registration metrics.
