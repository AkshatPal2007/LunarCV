# Implemented CV pipeline

The supported execution path is `backend/lunarcv/engine.py`, shared by CLI and API. See [overview](overview.md) and [evaluation protocol](../evaluation_protocol.md). Earlier SuperPoint/LoFTR snippets and illustrative performance numbers have been superseded; they are not current implementation claims.

1. Read actual PDS/raster headers and bounded windows; retain native radiometry, nodata validity, shape and crop origins. Compatible declared projected rasters derive overlap and scale; raw camera imagery needs explicit localization.
2. Normalize valid pixels with deterministic percentile stretch to uint8. No CLAHE/inversion/dilation/PCA in the default learned path.
3. Run pretrained ALIKED/LightGlue and bounded RIFT2. Rank primary matches with secondary agreement; retain documented primary fallback when the secondary fails. Coarse full-window geometry can guide bounded tiles. An empty coarse secondary result skips repeated secondary tile calls within the run.
4. Reject outliers with MAGSAC++ for affine/homography. Similarity uses OpenCV's RANSAC partial-affine estimator. Keep all candidate evidence in numeric NPZ.
5. Select top-ranked points per 4×4 source tile after outlier rejection. Measure occupancy, count CV and hull support over the whole processing window, including empty cells, in both images.
6. Attempt conservative paired local refinement before fitting the final transform. Reject unsupported refinements; zero accepted refinements is reported honestly.
7. Fit once to selected/refined points. Compose processing transforms into native source→native reference coordinates with pixel-center conventions.
8. Warp native radiometry to the reference processing grid; export science TIFF, masks, normalized PNG quicklooks, native CSV, transform, metrics and final artifact-hash manifest.
9. Evaluate independent controls only after registration if separately supplied. Fit residuals, candidate consistency and model confidence cannot establish independent accuracy.

Default gates remain fixed: at least 12 geometric inliers, ≥50% occupied grid cells in each image, ≥20% hull coverage in each image, CV ≤1.5 in each image, fit RMSE ≤2 native reference pixels. Even passing these gives geometrically usable/accuracy unvalidated, not a sub-pixel claim. The current development scene fails coverage gates.

RIFT2 optimization preserves original rounded histogram cells, bin edges and inclusive last edge exactly. Unit tests compare old per-cell histogram counts against the vectorized accumulation. Real fresh/cache output CSVs and native transforms are identical to the pre-optimization result.

TPS, general camera/orbit reprojection, DINOv2 retrieval, OmniGlue, and lunar domain fine-tuning are future work, not silently implemented fallbacks. Additional mission/polar/illumination cases and independent controls are required before scientific generalization claims.
