# 🌕 LunarCV: Cross-Sensor Remote Sensing Image Registration & Georeferencing Framework

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6+-ee4c2c.svg)](https://pytorch.org/)
[![Kornia](https://img.shields.io/badge/Kornia-0.8.3-green.svg)](https://kornia.github.io/)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.0+-red.svg)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**LunarCV** is an illumination-robust, cross-sensor feature matching and sub-pixel image registration framework for planetary orbital data. It registers heterogeneous lunar datasets across different space missions — primarily **ISRO Chandrayaan-2 (OHRC / TMC-2)** and **NASA LRO NAC** (Lunar Reconnaissance Orbiter Narrow Angle Camera).

---

## 🎯 The Scientific Problem & Benchmark Context

Cross-sensor image registration on planetary bodies presents severe challenges that break traditional feature matchers (SIFT, SURF, ORB):

1. **Extreme Resolution (GSD) Gap**: Chandrayaan-2 OHRC operates at **0.26 m/px**, whereas LRO NAC operates at **~1.60 m/px** (summed mode) — a **~6.15× spatial scale discrepancy**.
2. **Illumination & Shadow Variations**: Orbiting spacecraft capture terrain under drastically different solar incidence, emission, and azimuth angles, causing crater rims and shadows to cast in opposite directions.
3. **Low-Texture Regolith**: High-latitude and equatorial lunar regolith often exhibit low contrast and diffuse scattering.
4. **Large Data Volume**: Planetary images span gigabytes ($90,148 \times 12,000$ pixels for OHRC strips), requiring zero-copy streaming memory architectures.

### 🏆 Benchmark Reference to Beat
Our baseline is directly aligned with the published experiment by **Makharia et al.** (*ISRO SAC + Manipal University Jaipur*, IEEE InGARSS-adjacent benchmark):
* **Target Dataset Pair**: **OHRC-NAC Equatorial**
* **Published SuperGlue Benchmark RMSE**: **0.62 / 0.57 pixels**

---

## 🛰️ Verified Baseline Datasets

Both datasets have been verified for **100% geographic overlap** in the lunar equatorial region:

| Attribute | Source Image: Chandrayaan-2 OHRC | Reference Image: NASA LRO NAC |
| :--- | :--- | :--- |
| **Product ID** | `ch2_ohr_ncp_20210401T2357376656_d_img_d18` | `M1350459544RE.IMG` |
| **Instrument** | Orbiter High Resolution Camera (OHRC) | Narrow Angle Camera - Right (NAC-R) |
| **GSD (Resolution)** | **0.26 m/pixel** | **1.60 m/pixel** (1.55m × 1.66m) |
| **Dimensions** | **90,148 lines × 12,000 samples** (1.08 GB) | **52,224 lines × 2,532 samples** (132 MB) |
| **Data Format** | PDS4 UnsignedByte (`uint8`, offset 0) | PDS3 UnsignedByte (`uint8`, offset 5064) |
| **Latitude Range** | **-13.889° to -13.055°** | **-15.88° to -13.00°** |
| **Longitude Range** | **25.128° to 25.246°** | **25.08° to 25.41°** |
| **Overlap Status** | **100% of OHRC strip lies within the northern corridor of LRO NAC** | Contains entire OHRC coverage |

---

## 🏗️ Pipeline Architecture (CLAUDE.md v2)

```
REAL Chandrayaan-2 OHRC (source)         REAL NASA LRO NAC (reference)
        │                                             │
        ▼                                             ▼
  Metadata Extraction                           Metadata Extraction
  (GSD=0.26m, footprint, coords)               (GSD=1.60m, footprint, coords)
        └───────────────────────┬─────────────────────┘
                                ▼
                     Coarse Geographic Prior
                (scale ratio = 1.60 / 0.26 = 6.15x,
                 crop reference to candidate region)
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
  Minimal Normalization Only                      Minimal Normalization Only
  (percentile-stretch to uint8;                   (same, on cropped reference)
   NO CLAHE/inversion by default)
        └───────────────────────┬───────────────────────┘
                                ▼
                  Scale-Aligned Learned Matching
                  (LoFTR / LightGlue on GPU)
                                │
                                ▼
                    MAGSAC++ Outlier Rejection
                      (cv2.USAC_MAGSAC, tau=4.0px)
                                │
                                ▼
                Rigorous Evaluation & Verification
          (RMSE, Inlier Ratio, Match Count, Grid Occupancy)
                                │
                                ▼
                       Registered Product
```

---

## 📁 Project Directory Structure

```
LunarCV/
├── README.md                           # Comprehensive documentation & workflow guide
├── CLAUDE.md                           # Core project roadmap & scientific source of truth
├── pyproject.toml                      # Dependencies & package manifest
├── data/
│   ├── metadata/                       # Geographic footprint JSON metadata
│   ├── raw/
│   │   ├── tmc2/baseline/              # Chandrayaan-2 OHRC baseline product (.IMG, .XML, .CSV)
│   │   └── lro/                        # NASA LRO NAC baseline product (M1350459544RE.IMG)
│   └── processed/                      # Preprocessed arrays (.npy) and match points
├── outputs/
│   └── figures/                        # Generated visual overlays & diagnostic plots
└── src/
    ├── config.py                       # Central path, sensor GSD, and shape configurations
    ├── io_utils.py                     # Zero-copy memory mapping for OHRC, TMC-2, and LRO NAC
    ├── preprocessing.py                # Percentile normalization, CLAHE & Matplotlib helpers
    ├── matching.py                     # LoFTR matcher wrapper with VRAM budgeting
    ├── outlier_rejection.py            # MAGSAC++ geometric outlier filtering
    ├── validate_matches.py             # 4-panel visual alignment & perspective warping
    ├── transform_audit.py              # Per-inlier residual audit & synthetic unit tests
    ├── constrained_matching_pass.py    # 2nd-pass pre-aligned matching & 9-metric evaluator
    ├── test_new_baseline.py            # Quick verification of OHRC <-> LRO NAC ingestion
    └── main_baseline_ohrc_lro.py       # Primary baseline execution on OHRC <-> LRO NAC RE
```

---

## ⚡ Quickstart Commands

### 1. Ingestion & Scale Verification
Verifies zero-copy memory mapping, sensor geometry, and scale ratio:
```bash
uv run python src/test_new_baseline.py
```

### 2. Run the OHRC ↔ LRO NAC Baseline Registration
Executes the evidence-based baseline pipeline on the new experimental pair:
```bash
uv run python src/main_baseline_ohrc_lro.py
```

### 3. Run the Transform Audit & Synthetic Unit Tests
Verifies mathematical transformation consistency ($< 10^{-4}\text{ px}$ error verification):
```bash
uv run python src/transform_audit.py
```

---

## 📊 Latest Experimental Results (OHRC ↔ LRO NAC RE)

Running on the real Chandrayaan-2 OHRC and NASA LRO NAC (`M1350459544RE`) baseline pair.

We have implemented a **Spatially Constrained Matching** pipeline (`src/spatially_constrained_matching.py`) that applies 4x4 Grid Uniformity and Confidence Filtering to prevent MAGSAC++ from overfitting to micro-clusters.

| Metric | Current Spatially Constrained Result (Exp D) | Acceptance Criteria | Status |
| :--- | :--- | :--- | :--- |
| **Candidate Matches** | **160** (filtered from 525) | - | ✅ Spatial distribution forced |
| **MAGSAC++ Inliers** | **7** | $\ge 15$ | ❌ Failed to find 15 inliers |
| **Grid Occupancy** | **25.0%** (4 / 16 cells) | $> 50\%$ | ❌ Highly localized |
| **Convex Hull Coverage** | **17.78%** | $> 30\%$ | ❌ Highly localized |
| **Symmetric RMSE** | **1.79 px** | $< 3.0\text{ px}$ | ✅ Low training error |
| **Cross-Validation RMSE** | **55.68 px** | Reasonable | ❌ Massive overfitting/distortion |

### Verdict: **REJECTED**
Despite implementing rigorous spatial uniformity constraints, the pipeline failed to extract a globally consistent registration. The underlying LoFTR matcher is only finding reliable features in 4 localized micro-clusters. Forcing spatial diversity causes the geometric model (Affine/Homography) to fit a highly distorted, physically implausible transformation (evident by the 55.68 px CV error).

**Next Bottleneck:** The correspondence generation (matcher) itself is struggling with the low-texture, high-ambiguity lunar regolith. We need to experiment with alternative matchers (e.g., LightGlue, RIFT2) or revisit preprocessing enhancements (e.g., CLAHE) to boost feature distinctiveness.
