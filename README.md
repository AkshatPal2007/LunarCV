# 🌕 LunarCV: Cross-Sensor Remote Sensing Image Registration & Georeferencing Framework

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6+-ee4c2c.svg)](https://pytorch.org/)
[![Kornia](https://img.shields.io/badge/Kornia-0.8.3-green.svg)](https://kornia.github.io/)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.0+-red.svg)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**LunarCV** is an illumination-robust, cross-sensor feature matching and sub-pixel image registration framework for planetary orbital data. It is specifically designed to register heterogeneous lunar datasets across different space agencies — namely **ISRO Chandrayaan-2 TMC-2** (Terrain Mapping Camera-2) and **NASA LRO NAC** (Lunar Reconnaissance Orbiter Narrow Angle Camera).

---

## 🎯 The Scientific Problem

Cross-sensor image registration on planetary bodies presents severe challenges that break traditional feature matchers (SIFT, SURF, ORB):

1. **Extreme Resolution (GSD) Gap**: Chandrayaan-2 TMC-2 operates at **~5.0 m/px**, whereas LRO NAC operates at **~0.5 m/px** — a **10× spatial scale discrepancy**.
2. **Illumination & Shadow Variations**: Orbiting spacecraft capture terrain under drastically different solar incidence, emission, and azimuth angles, causing crater rims and shadows to flip direction.
3. **Low-Texture Regolith**: High-latitude and equatorial lunar regolith often exhibit low contrast and diffuse scattering.
4. **Large Data Volume**: Planetary images span gigabytes ($148,108 \times 4,000$ pixels for TMC-2 strips), requiring zero-copy streaming memory architectures.

---

## 🏗️ Pipeline Architecture & Methodology

```
+-----------------------------------------------------------------------------------+
| 1. Binary Ingestion & Zero-Copy Streaming                                         |
|    - Memory-map raw binary PDS .IMG files (np.memmap) without RAM loading         |
|    - Parse PDS3 ASCII headers (RECORD_BYTES, LINES, SAMPLES, offsets)             |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 2. Preprocessing & Contrast Stretching                                            |
|    - Percentile-based stretching: uint16 [2%, 98%] percentile clip -> uint8       |
|    - Contrast-Limited Adaptive Histogram Equalization (OpenCV CLAHE)              |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 3. Scale-Matching & Aspect Ratio Alignment                                        |
|    - Downsample LRO NAC by 10x (INTER_AREA) to align GSD (~5.0 m/px)              |
|    - Match aspect ratio & resize for transformer VRAM budgeting                   |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 4. Detector-Free Feature Matching                                                 |
|    - Kornia LoFTR (Local Feature TRansformer) outdoor pretrained model             |
|    - Dense cross-attention feature extraction on GPU                              |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 5. Geometric Outlier Rejection                                                    |
|    - OpenCV MAGSAC++ (cv2.USAC_MAGSAC) with reprojection threshold tau = 5.0 px   |
|    - Directionally verified Homography H mapping LRO NAC -> TMC-2                 |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 6. 9-Metric Rigorous Verification & Warped Overlay Suite                          |
|    - Compute Forward/Backward RMSE, Symmetric Error, 5-Fold Cross Validation      |
|    - Evaluate 4x4 Grid Occupancy & Spatial Convex Hull Area                       |
|    - Generate 4-panel visual alignment (TMC-2, Warped LRO, Alpha Blend, Checker)  |
+-----------------------------------------------------------------------------------+
```

---

## 📁 Project Directory Structure

```
LunarCV/
├── README.md                           # Comprehensive documentation & workflow guide
├── pyproject.toml                      # Dependencies & package manifest
├── data/
│   ├── metadata/                       # Geographic footprint JSON metadata
│   │   └── tmc2_patch_bbox.json        # Latitude/Longitude bounds of TMC-2 patch
│   ├── raw/
│   │   ├── tmc2/                       # Raw Chandrayaan-2 TMC-2 binary product (.IMG)
│   │   └── lro/                        # Raw LRO NAC PDS binary product (.IMG)
│   └── processed/                      # Preprocessed arrays (.npy) and match points
│       ├── tmc2/                       # Processed TMC-2 patches (.npy)
│       ├── lro/                        # Scale-matched LRO NAC patches (.npy)
│       └── matches/                    # Homography matrices and inlier keypoints (.npy)
├── outputs/
│   └── figures/                        # Generated 4-panel visual alignment overlays
└── src/
    ├── config.py                       # Global directory paths and sensor shape specifications
    ├── io_utils.py                     # PDS label parser & zero-copy memmap loaders
    ├── preprocessing.py                # Percentile normalization, CLAHE & Matplotlib helpers
    ├── matching.py                     # LoFTR wrapper with automatic VRAM scaling
    ├── outlier_rejection.py            # MAGSAC++ geometric outlier rejection
    ├── validate_matches.py             # 4-panel visual alignment suite & perspective warping
    ├── transform_audit.py              # Per-inlier residual audit & synthetic unit tests
    ├── constrained_matching_pass.py    # 2nd-pass pre-aligned matching & 9-metric evaluator
    └── main_phase3.py                  # End-to-end baseline pipeline runner
```

---

## 🔬 Core Source Modules Explained

| Module | Description & Primary Functionality |
| :--- | :--- |
| **`config.py`** | Central configuration file defining project paths (`DATA_DIR`, `OUTPUT_DIR`), sensor dimensions (`148108 × 4000` for TMC-2), and automatic directory creation on import. |
| **`io_utils.py`** | Implements zero-copy memory mapping (`load_tmc2_memmap`, `load_lro_nac_memmap`) and PDS3 ASCII label parsing (`parse_lro_pds_header`) to calculate byte offsets. |
| **`preprocessing.py`** | Houses `normalize_uint16_to_uint8()` for percentile clipping, `apply_clahe()` for contrast enhancement, and matplotlib figure export utilities. |
| **`matching.py`** | Wraps Kornia's detector-free `LoFTR` model (`outdoor` weights). Implements automatic dimension scaling (`max_dim=1024`) to prevent PyTorch CUDA Out-Of-Memory (OOM) errors on 8GB GPUs, automatically scaling keypoints back to original space. |
| **`outlier_rejection.py`** | Applies OpenCV MAGSAC++ (`cv2.findHomography` with `cv2.USAC_MAGSAC`) to filter false correspondences and fit a directionally verified Homography $H$ mapping LRO NAC $\to$ TMC-2. |
| **`validate_matches.py`** | Computes forward/backward reprojection errors, performs perspective warping (`cv2.warpPerspective`), and exports a 4-panel visual validation suite (TMC-2, Warped LRO, 50/50 Alpha Blend, 150px Checkerboard). |
| **`transform_audit.py`** | Contains synthetic unit tests ($< 10^{-4}\text{ px}$ error verification) and prints per-inlier residual error tables using `cv2.perspectiveTransform` to verify mathematical logic. |
| **`constrained_matching_pass.py`** | Executes 2nd-pass pre-aligned matching and evaluates the complete **9-metric registration report** (including 5-fold cross validation and $4 \times 4$ spatial grid occupancy). |
| **`main_phase3.py`** | Primary command-line integration script running the full end-to-end processing, matching, filtering, and visualization pipeline. |

---

## 📊 The 9 Evaluation Metrics & Acceptance Thresholds

For a registration between two lunar scenes to be accepted as production-ready, **LunarCV** evaluates 9 quantitative metrics:

| Metric | Description | Target Threshold |
| :--- | :--- | :--- |
| **1. Inlier Count** | Total number of geometrically verified inliers after MAGSAC++ | $\ge 15\text{ points}$ |
| **2. Confidence Distribution** | Min, Median, Mean, and Max LoFTR match confidence scores | High mean/median ($> 0.40$) |
| **3. Convex Hull Coverage** | Spatial area of the inlier convex hull relative to total image area | $> 30\%$ of patch area |
| **4. Minimum Separation** | Minimum Euclidean distance between adjacent inliers | $> 10.0\text{ pixels}$ |
| **5. Grid-Cell Occupancy** | Percentage of occupied cells in a $4 \times 4$ spatial grid (16 cells) | $> 50\%$ (at least $8/16$ cells) |
| **6. Forward RMSE** | Reprojection RMSE mapping LRO $\to$ TMC-2 using $H$ | $< 3.0\text{ pixels}$ |
| **7. Backward RMSE** | Reprojection RMSE mapping TMC-2 $\to$ LRO using $H^{-1}$ | $< 5.0\text{ pixels}$ |
| **8. Symmetric Error** | Average of forward and backward transfer errors | $< 3.0\text{ pixels}$ |
| **9. 5-Fold Cross Validation** | Reprojection RMSE on held-out test points using 5-fold cross-validation | $< 10.0\text{ pixels}$ |

---

## ⚡ Execution Commands

### 1. Run the Main Registration Pipeline
```bash
uv run python src/main_phase3.py
```

### 2. Run the Transform Audit & Synthetic Unit Test
```bash
uv run python src/transform_audit.py
```

### 3. Run the 2nd-Pass Constrained Evaluator
```bash
uv run python src/constrained_matching_pass.py
```

---

## 📈 Recent Findings & Audit Status

* ✅ **Mathematical & Transform Integrity**: Verified via `src/transform_audit.py`. Synthetic unit tests passed with **$0.000065\text{ px}$ RMSE**. Homography direction ($H_{\text{LRO}\to\text{TMC2}}$) is 100% verified.
* ✅ **Sub-Pixel Local Precision**: Verified. Inliers exhibit sub-pixel local accuracy (**$RMSE = 0.3261\text{ px}$**, **$\text{Median Error} = 0.1298\text{ px}$**).
* ⚠️ **Spatial Coverage & Inlier Count**: In the current test patch, 5 inliers occupy 8.32% of the patch area (25% grid occupancy), resulting in a 5-fold cross-validation error of 106.8 px outside the local cluster.
* 📌 **Current Recommendation**: Maintain provisional inlier evidence and perform exact geographic footprint overlap cropping before final Phase 4 sign-off.

---

## 📜 Technical Dependencies
* **Python 3.11+**
* **PyTorch 2.6+** (CUDA 12.4 enabled)
* **Kornia 0.8.3** (LoFTR pretrained feature weights)
* **OpenCV 5.0+** (USAC_MAGSAC, warpPerspective, CLAHE)
* **NumPy, SciPy, Matplotlib, Pandas, PyProj, Rasterio**
