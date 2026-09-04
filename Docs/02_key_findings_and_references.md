# Key Findings and References

## Key Findings

### 1. Learned matching is the strongest primary direction

The related benchmark found that off-the-shelf SuperGlue performed best across the tested sensor pairs and regions, including difficult polar cases. This supports using a pretrained learned matcher as the primary path instead of relying on a classical feature detector alone.

LunarCV uses LightGlue with SuperPoint as the current learned matching implementation. LightGlue is a faster, MIT-licensed successor in the same practical family of pretrained matching tools.

### 2. RIFT2 is a valuable independent matcher

RIFT2 uses phase congruency and was the strongest classical-style method in the benchmark. It required no heavy preprocessing and is designed to be less sensitive to illumination changes. It is therefore used as a complementary matcher and a source of cross-validation, rather than as the only matcher.

The benchmark also recorded RIFT2 failures in some polar and SAR cases. The pipeline must preserve a learned-matcher fallback instead of assuming that every matcher works on every region.

### 3. Heavy preprocessing should not be the default

CLAHE, inversion, dilation, and PCA helped traditional methods become usable, but the benchmark showed that this preprocessing-heavy path still lost to the unpreprocessed learned matcher. The primary pipeline therefore uses percentile stretching and scale alignment only. Heavy preprocessing remains an optional documented fallback for classical experiments.

### 4. Spatial uniformity is a project differentiator

The benchmark measured accuracy and execution time but did not enforce a spatially uniform match distribution. LunarCV adds grid-based selection after geometric outlier rejection. The goal is to avoid a transform being supported by a dense cluster of matches in only one part of the image.

Spatial uniformity is reported as the coefficient of variation of match counts across grid tiles. A lower value indicates a more even distribution, but it must be considered together with match count and inlier quality.

### 5. Sub-pixel accuracy requires independent evidence

A low reprojection RMSE alone does not prove real sub-pixel registration accuracy because the same matches used to fit a transform can also make its residuals look small. Any sub-pixel claim must be checked with an independent real signal, such as shared crater centroids, orbit-metadata reprojection, or agreement across multiple overlapping sensor images.

### 6. Reported metrics must remain honest

No hand-picked matches, fabricated data, or synthetic evaluation images may be used. Every reported number must identify its real source pair, processing configuration, model, and validation method. Uncertainty and failed cases should be reported alongside successful cases.

## Baseline Numbers to Beat

The project brief records the following SuperGlue RMSE values from Makharia et al. These are comparison targets, not LunarCV results:

| Dataset pair and region | Reported RMSE (pixels) |
| --- | ---: |
| OHRC-NAC equatorial | 0.62 / 0.57 |
| OHRC-NAC polar | 0.92 / 0.76 |
| IIRS-WAC equatorial | 0.51 / 0.62 |
| IIRS-WAC polar | 0.77 / 0.93 |
| DFSAR-SELENE equatorial | 0.39 / 0.84 |
| DFSAR-SELENE polar | 0.92 / 0.76 |

The exact meaning of the paired values must be checked against the source paper before presenting them as separate directional metrics. LunarCV should report its own measured values separately from this reference baseline.

## References Used

### Project and dataset references

1. **SIH problem statement and project brief** in the repository's `CLAUDE.md`. This defines the sensors, failure modes, hard constraints, deliverables, and required evaluation metrics.
2. **Chandrayaan-2 data portal:** https://chmapbrowse.issdc.gov.in/
3. **LROC image downloads:** https://lroc.im-ldi.com/images/downloads/
4. **LROC QuickMap:** https://quickmap.lroc.im-ldi.com/
5. **LROC EDR search:** https://wms.lroc.asu.edu/lroc/search
6. **SELENE/Kaguya imagery** as the second reference mission.

For LROC geographic searches, use West/East longitude and South/North latitude fields. Do not use Sub-Solar Longitude/Latitude fields for geographic footprint selection.

### Related research

7. **Makharia et al.**, “Comparative Evaluation of Traditional and Deep Learning Feature Matching Algorithms using Chandrayaan-2 Lunar Data.” This is the main benchmark used for the SuperGlue, SIFT, ASIFT, AKAZE, and RIFT2 findings and comparison targets recorded in the project brief.

### Software and algorithm references

8. **LightGlue:** pretrained feature matching implementation from the CVG group, used with SuperPoint features.
9. **RIFT2:** phase-congruency-based multimodal image matching implementation stored under `src/third_party/rift2/`.
10. **OpenCV MAGSAC++:** `cv2.USAC_MAGSAC`, used for robust geometric outlier rejection.
11. **OpenCV sub-pixel tools:** `cv2.cornerSubPix` and `cv2.calcOpticalFlowPyrLK`.
12. **DINOv2 and OmniGlue:** optional future components for large-mosaic retrieval or a stretch matcher; they are not required for the baseline.

All model and software choices must remain free/open-source and use pretrained weights where available.
