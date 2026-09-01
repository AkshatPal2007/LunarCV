# Lunar Multi-Modal Image Registration — SIH Project

## Problem Statement (source of truth — do not deviate)

Build a generic software solution that finds **sub-pixel accurate, spatially
uniform correspondence points** between:

- **Source images**: Chandrayaan-2 optical payloads — OHRC, TMC-2, IIRS
- **Reference images**: LRO NAC (Lunar Reconnaissance Orbiter Narrow Angle
  Camera), SELENE

The registration must be robust to three challenges named explicitly in the
problem statement:

1. **Illumination variation** — sun azimuth/elevation changes surface shading
2. **Viewpoint variation** — geometric distortion from different camera
   positions/orientations
3. **Scale variation** — large GSD/altitude differences across missions

**Deliverables**: working software, a registered output product with match
points, and an evaluation report (RMSE, inlier count, inlier ratio, spatial
uniformity).

## Hard Constraints (non-negotiable)

- **No fabricated/synthetic data in any evaluation or demo.** All reported
  results must come from real Chandrayaan-2 (OHRC/TMC-2/IIRS) and real LRO
  NAC / SELENE imagery.
- The **only** permitted use of synthetic/rendered data is optional
  self-supervised pretraining, and only if rendered from real DEM/terrain
  data (LOLA, SLDEM2015, Chandrayaan-2 TMC DEM) — must be clearly labeled as
  a pretraining step, never mixed into evaluation numbers.
- Never hand-pick convenient "ground truth" matches to inflate metrics. Use
  geometrically-derived correspondences (orbit metadata reprojection,
  cross-sensor consistency checks) as the best approximation of truth, and
  report uncertainty honestly.
- Don't claim sub-pixel accuracy without actually measuring it against a
  real independent check (e.g., common crater centroids visible in both
  images).
- **Hackathon mode, not research mode**: use existing free/open-source
  pretrained models wherever possible. Do not train models from scratch
  unless there is no viable pretrained alternative. Novelty comes from
  pipeline composition and domain adaptation, not from inventing new
  architectures.

## Datasets

- Chandrayaan-2 orbiter data: https://chmapbrowse.issdc.gov.in/
- LRO NAC: https://lroc.im-ldi.com/images/downloads/ ,
  https://quickmap.lroc.im-ldi.com/ , EDR search:
  https://wms.lroc.asu.edu/lroc/search
- SELENE images (Kaguya)
- Coordinate range search fields: West/East = longitude, South/North =
  latitude. Do NOT use the Sub-Solar Longitude/Latitude fields for a
  footprint search — those filter by illumination geometry, not location.

## Related Work — Benchmark to Beat

Makharia et al., "Comparative Evaluation of Traditional and Deep Learning
Feature Matching Algorithms using Chandrayaan-2 Lunar Data" (ISRO SAC +
Manipal University Jaipur, IEEE InGARSS-adjacent work) benchmarked SIFT,
ASIFT, AKAZE, RIFT2, and SuperGlue across OHRC-NAC, IIRS-WAC, and
DFSAR-SELENE pairs, equatorial and polar regions. Key findings that shape
our strategy:

- **SuperGlue won every dataset pair** on both RMSE and execution time,
  including polar cases where SIFT/ASIFT/AKAZE/RIFT2 completely failed
  (OHRC-NAC Polar, DFSAR-SELENE Equatorial/Polar).
- **RIFT2 (phase congruency based) needed no preprocessing** and was the
  best-performing classical-style method, validating illumination-invariant
  phase congruency as a real, literature-backed technique for this domain.
- **Heavy preprocessing (CLAHE, inversion, dilation, PCA) was only needed to
  make classical methods usable at all** (SIFT/ASIFT/AKAZE), and even then
  those methods still lost to unpreprocessed SuperGlue and RIFT2 on both
  accuracy and speed. Preprocessing-heavy pipelines are not the winning
  approach for the learned-matcher path.
- **Their evaluation never measured or enforced spatial distribution
  uniformity** — RMSE and execution time only. This is a clear, documented
  gap relative to our problem statement's explicit uniformity requirement.
- They used **off-the-shelf SuperGlue with zero domain-specific fine-tuning**
  and it still won — meaning there is real headroom above their reported
  numbers for anyone who fine-tunes on lunar data specifically.
- Reported RMSE (pixels) for SuperGlue: OHRC-NAC Equatorial 0.62/0.57,
  OHRC-NAC Polar 0.92/0.76, IIRS-WAC Equatorial 0.51/0.62, IIRS-WAC Polar
  0.77/0.93, DFSAR-SELENE Equatorial 0.39/0.84, DFSAR-SELENE Polar 0.92/0.76.
  Use these as the baseline numbers our pipeline should target and beat.

## Final Architecture (v2 — evidence-updated)

```
REAL Chandrayaan-2 (source)              REAL LRO NAC / WAC / SELENE (reference)
        │                                          │
        ▼                                          ▼
  Metadata Extraction                      Metadata Extraction
  (GSD, footprint, coords, sun angle)      (GSD, footprint, coords)
        └───────────────┬──────────────────────────┘
                         ▼
              Coarse Geographic Prior
         (crop reference to candidate region,
          estimate scale ratio from GSDs)
                         │
        ┌────────────────┴────────────────┐
        ▼                                  ▼
  Minimal normalization only         Minimal normalization only
  (percentile-stretch to uint8;      (same, on cropped reference
   NO CLAHE/inversion/dilation/PCA    region)
   by default — evidence shows it
   doesn't help the learned matcher)
        └────────────────┬────────────────┘
                         ▼
        ┌────────────────────────────────────┐
        │   Primary matcher: LightGlue        │
        │   (SuperGlue's faster, MIT-licensed │
        │   successor — pretrained, no        │
        │   fine-tuning needed for baseline)  │
        │                                      │
        │   Secondary matcher: RIFT2           │
        │   (phase congruency — run in         │
        │   parallel for cross-validation)     │
        └────────────────┬────────────────────┘
                         ▼
        Cross-validate: keep high-confidence
        matches where both agree; fall back to
        LightGlue-only where RIFT2 fails
        (their documented polar/SAR failure cases)
                         │
                         ▼
              MAGSAC++ Outlier Rejection
                         │
                         ▼
            Grid-based Spatial Distribution
         (top-K matches per tile — NOT present
          in the reference paper; our differentiator)
                         │
                         ▼
      Local Sub-Pixel Correlation + Peak Interpolation
              (cornerSubPix / Lucas-Kanade)
                         │
                         ▼
     Transform Estimation
     (Similarity/Affine/Homography; TPS fallback
      for high-relief / terminator / polar regions)
                         │
                         ▼
                Registered Image
                         │
                         ▼
             Evaluation Dashboard
      (RMSE, Inlier Ratio, Match Count, Spatial
       Uniformity, Registration Error — reported
       against the paper's Table 3 as baseline)
```

### Why this order (don't re-derive, just follow it)

- Metadata/geographic prior runs **first** — turns "search the whole Moon"
  into "search this tile," faster and more accurate.
- Preprocessing is deliberately minimal now — the benchmark paper's own
  results show heavy preprocessing (CLAHE/inversion/dilation/PCA) was a
  crutch for classical methods that still lost to unpreprocessed learned
  matchers. Don't reintroduce that overhead for the primary path.
- LightGlue + RIFT2 run in parallel, not just LightGlue alone — this
  exploits their complementary failure patterns rather than betting
  everything on one matcher.
- MAGSAC++ runs **before** grid-based spatial distribution — reject
  geometrically wrong matches first, then enforce spatial coverage on the
  clean set.
- Sub-pixel refinement happens **before** final transform fitting, not
  after — the transform is only as accurate as the points fed into it.

## Model / Library Choices (all free, open-source, pretrained)

| Stage | Choice | Notes |
|---|---|---|
| Primary learned matcher | **LightGlue** | MIT license, faster + more accurate successor to SuperGlue (which the benchmark paper used and still won with) |
| Secondary matcher | **RIFT2** | Phase congruency based, no preprocessing needed, validated by benchmark paper as best classical-style performer |
| Stretch matcher (radical) | **OmniGlue** (Apache 2.0) | DINOv2-guided generalist matcher; untested in the benchmark paper — genuine novelty vs. published work |
| Coarse retrieval (large mosaic case) | **DINOv2** (Meta, Apache 2.0) | Patch-level retrieval to localize source within a big reference mosaic |
| Outlier rejection | **OpenCV MAGSAC++** (`cv2.USAC_MAGSAC`) | Built into OpenCV |
| Transform / warp | OpenCV homography/affine + `cv2.createThinPlateSplineShapeTransformer` | TPS for relief-heavy/polar regions |
| Sub-pixel refinement | `cv2.cornerSubPix`, `cv2.calcOpticalFlowPyrLK` | Built into OpenCV |
| Fallback classical (optional, not primary) | SIFT/AKAZE + CLAHE/inversion/dilation/PCA | Only as a documented fallback demo; evidence shows it's not the winning path |

Do not introduce paid APIs or closed-weight models anywhere in the pipeline.

## Evaluation Metrics (must be reported for every test pair)

- **RMSE** of matched point residuals after transform — report against the
  benchmark paper's Table 3 numbers per dataset pair
- **Inlier ratio** (MAGSAC++ inliers / total candidate matches)
- **Match count**
- **Spatial uniformity** — coefficient of variation of match count per grid
  tile (lower = more uniform = better) — this metric is absent from the
  reference paper; report it as a distinguishing contribution
- **Execution time** per stage — the paper treats this as a key comparison
  axis, match it
- **Registration error** cross-checked against an independent signal where
  possible (shared crater centroids, orbit-metadata reprojection, or
  agreement across 3+ overlapping sensor images)

## Project Structure

```
LunarCV/
├── .gitignore
├── README.md
├── pyproject.toml
├── .env.example
│
├── data/
│   ├── raw/
│   └── processed/
│
├── outputs/
│   └── figures/
│
├── src/
│   └── lunarcv/
│       ├── __init__.py
│       ├── config.py
│       ├── io/
│       │   ├── __init__.py
│       │   └── raster.py
│       ├── preprocessing/
│       │   ├── __init__.py
│       │   ├── normalize.py
│       │   └── visualize.py
│       ├── matching/
│       │   ├── __init__.py
│       │   ├── lightglue_matcher.py
│       │   ├── rift2_matcher.py
│       │   └── ensemble.py          # cross-validation between matchers
│       ├── registration/
│       │   ├── __init__.py
│       │   ├── outlier_rejection.py  # MAGSAC++
│       │   ├── spatial_uniformity.py # grid-based top-K
│       │   ├── subpixel.py
│       │   └── transform.py
│       └── evaluation/
│           ├── __init__.py
│           └── metrics.py
│
├── scripts/
│   ├── preprocess_patch.py
│   └── register_pair.py             # end-to-end CLI entrypoint
│
├── notebooks/
├── tests/
├── docs/
│   └── CLAUDE.md
└── frontend/
    └── README.md
```

## Working Conventions for this Session

- Prefer OpenCV / kornia / existing pretrained weights over custom
  reimplementation whenever an equivalent free tool exists.
- Every function that touches imagery must accept real file paths — no
  placeholder/random arrays standing in for lunar images in demos or
  reported results. Synthetic arrays are fine only for unit-testing code
  logic, never for producing reported numbers.
- When downloading or referencing datasets, always use the real ISSDC/LROC/
  SELENE sources listed above.
- When searching LROC EDR search tool, use the Coordinate Range fields
  (West/East/South/North), never the Sub-Solar Longitude/Latitude fields,
  for a location-based search.
- Flag clearly in code comments/README any stage that is a placeholder
  pending real data access.
- Don't default to heavy preprocessing (CLAHE/inversion/dilation/PCA) for
  the primary learned-matcher path — evidence shows it doesn't help and
  adds overhead. Reserve it for an optional classical-method fallback path.

## Milestones

1. Data acquisition + minimal normalization pipeline (real overlapping
   OHRC/TMC/IIRS + LRO NAC/WAC pairs)
2. Baseline: geographic prior + LightGlue + MAGSAC++ — working end-to-end
   demo, benchmark against the paper's SuperGlue RMSE numbers
3. Add RIFT2 as parallel secondary matcher + cross-validation ensemble
4. Add grid-based spatial uniformity + sub-pixel refinement
5. Breakthrough layer: attempt domain-adapted fine-tuning targeting the
   paper's documented failure cases (OHRC-NAC Polar, DFSAR-SELENE
   Equatorial), and/or OmniGlue/DINOv2 as an untested generalist layer
6. Evaluation dashboard (RMSE vs. paper baseline, inlier ratio, uniformity,
   execution time, registration error)
7. Package as CLI/web tool producing registered product + match point file
   + metrics report
