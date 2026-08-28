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
- Don't claim sub-pixel accuracy without actually measuring it against an
  independent check (e.g., common crater centroids visible in both images).
- **Hackathon mode, not research mode**: use existing free/open-source
  pretrained models wherever possible. Do not train models from scratch
  unless there is no viable pretrained alternative. Novelty comes from
  pipeline composition and domain adaptation, not from inventing new
  architectures.

## Datasets

- Chandrayaan-2 orbiter data: https://chmapbrowse.issdc.gov.in/
- LRO NAC: https://lroc.im-ldi.com/images/downloads/ ,
  https://quickmap.lroc.im-ldi.com/
- SELENE images (Kaguya)
- Specific dataset pairing links: TBD from organizers — until provided,
  source overlapping-coverage pairs manually via QuickMap/ISSDC browse tools.

## Final Architecture

```
REAL Chandrayaan-2 (source)              REAL LRO NAC / SELENE (reference mosaic)
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
  CLAHE + Phase Congruency          CLAHE + Phase Congruency
  (source, multi-scale pyramid)      (reference, cropped region)
        └────────────────┬────────────────┘
                         ▼
              Learned Matcher (LoFTR / LightGlue,
                 pretrained, no fine-tuning)
                         │
                         ▼
              Candidate Matches
                         │
                         ▼
              MAGSAC++ Outlier Rejection
                         │
                         ▼
            Grid-based Spatial Distribution
              (top-K matches per tile)
                         │
                         ▼
      Local Sub-Pixel Correlation + Peak Interpolation
              (cornerSubPix / Lucas-Kanade)
                         │
                         ▼
     Transform Estimation
     (Similarity/Affine/Homography; TPS fallback
      for high-relief / terminator regions)
                         │
                         ▼
                Registered Image
                         │
                         ▼
             Evaluation Dashboard
      (RMSE, Inlier Ratio, Match Count, Spatial
       Uniformity, Registration Error)
```

### Why this order (don't re-derive, just follow it)

- Metadata/geographic prior runs **first**, before any pixel-level work —
  turns "search the whole Moon" into "search this tile," which is both
  faster and more accurate.
- Phase congruency (not just CLAHE) is the actual answer to illumination
  invariance — CLAHE fixes contrast, not the fact that a crater rim is a
  bright edge under one sun angle and a dark edge under another.
- MAGSAC++ runs **before** grid-based spatial distribution — reject
  geometrically wrong matches first, then enforce spatial coverage on the
  clean set. Doing it the other way risks keeping a spatially-convenient
  but wrong match over a tile's only good one.
- Sub-pixel refinement happens **before** final transform fitting, not
  after — the transform is only as accurate as the points fed into it.

## Model / Library Choices (all free, open-source, pretrained)

| Stage | Choice | Notes |
|---|---|---|
| Learned matcher | **LoFTR** (via `kornia.feature.LoFTR`) | Primary — detector-free, robust on low-texture terrain |
| Learned matcher (alt/speed) | **LightGlue** | MIT license, faster, good demo latency |
| Cross-domain generalization (stretch/"radical" pitch) | **OmniGlue** (Apache 2.0) | DINOv2-guided, built for exactly this generalization problem |
| Coarse retrieval (if reference is a huge mosaic) | **DINOv2** (Meta, Apache 2.0) | Patch-level retrieval to localize source within mosaic |
| Outlier rejection | **OpenCV MAGSAC++** (`cv2.USAC_MAGSAC`) | Built into OpenCV, no extra dependency |
| Transform / warp | OpenCV homography/affine + `cv2.createThinPlateSplineShapeTransformer` | TPS for relief-heavy regions |
| Sub-pixel refinement | `cv2.cornerSubPix`, `cv2.calcOpticalFlowPyrLK` | Built into OpenCV |
| Illumination invariance | Phase congruency (Kovesi's method) | Implement or adapt existing open implementations (e.g. `phasepack`) |

Do not introduce paid APIs or closed-weight models anywhere in the pipeline.

## Evaluation Metrics (must be reported for every test pair)

- **RMSE** of matched point residuals after transform
- **Inlier ratio** (MAGSAC++ inliers / total candidate matches)
- **Match count**
- **Spatial uniformity** — coefficient of variation of match count per grid
  tile (lower = more uniform = better)
- **Registration error** cross-checked against an independent signal where
  possible (shared crater centroids, orbit-metadata reprojection, or
  agreement across 3+ overlapping sensor images)

## Project Structure (proposed)

```
/data/                # real downloaded imagery only — never commit large raw files
  /chandrayaan2/
  /lro_nac/
  /selene/
/src/
  metadata.py         # extract GSD, footprint, coords from image headers/labels
  preprocessing.py     # CLAHE, phase congruency, multi-scale pyramid
  geo_prior.py         # coarse geographic cropping + scale estimation
  matching.py          # LoFTR/LightGlue/OmniGlue wrappers
  outlier_rejection.py # MAGSAC++ wrapper
  spatial_uniformity.py# grid-based top-K filtering
  subpixel.py          # cornerSubPix / Lucas-Kanade refinement
  transform.py         # similarity/affine/homography/TPS fitting + warping
  evaluate.py          # RMSE, inlier ratio, uniformity, reporting
/notebooks/            # exploration only — final pipeline must run as scripts/CLI
/outputs/              # registered images, match point files, metric reports
requirements.txt
README.md
```

## Working Conventions for this Session

- Prefer OpenCV / kornia / existing pretrained weights over custom
  reimplementation whenever an equivalent free tool exists.
- Every function that touches imagery must accept real file paths — no
  placeholder/random arrays standing in for lunar images in demos or
  reported results. Synthetic arrays are fine only for unit-testing code
  logic (e.g., verifying a homography math function), never for producing
  numbers that get reported as results.
- When downloading or referencing datasets, always use the real ISSDC/LROC/
  SELENE sources listed above.
- Flag clearly in code comments/README any stage that is a placeholder
  pending real data access (e.g., if a specific dataset link is still TBD).

## Milestones

1. Data acquisition + preprocessing pipeline (real overlapping OHRC/TMC/IIRS
   + LRO NAC pairs, radiometric normalization)
2. Baseline: geographic prior + phase congruency + LoFTR + MAGSAC++ —
   working end-to-end demo
3. Add grid-based spatial uniformity + sub-pixel refinement
4. Stretch: OmniGlue/DINOv2 layer for the "radical approach" pitch
5. Evaluation dashboard (RMSE, inlier ratio, uniformity, registration error)
6. Package as CLI/web tool producing registered product + match point file
   + metrics report
