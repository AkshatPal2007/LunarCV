# 🌕 LunarCV

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6+-ee4c2c.svg)](https://pytorch.org/)
[![Kornia](https://img.shields.io/badge/Kornia-0.8.3-green.svg)](https://kornia.github.io/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**LunarCV** is an advanced computer vision framework for cross-mission planetary image registration. 

When different satellites (like India's **Chandrayaan-2** and NASA's **Lunar Reconnaissance Orbiter**) photograph the Moon, they capture the terrain at completely different resolutions, from different angles, and under opposite shadow conditions. This makes aligning the images incredibly difficult for traditional mapping software.

LunarCV solves this by combining modern Deep Learning algorithms with advanced geometric filters to automatically find matching craters and perfectly align the images into a single coordinate system.

---

## ✨ Features

- **Ensemble Matching Architecture:** Runs multiple algorithms in parallel to overcome lunar domain challenges:
  - **LoFTR:** Dense transformer-based matching for robust feature tracking.
  - **LightGlue (DISK):** High-speed sparse feature matching.
  - **RIFT2:** Phase-congruency matching that is mathematically immune to severe shadow reversals.
- **Advanced Outlier Rejection:** Uses **MAGSAC++** alongside custom Spatial Uniformity Grid filters to prevent the algorithm from hallucinating matches in highly repetitive regolith.
- **Zero-Copy Memory Mapping:** Capable of processing massive 1GB+ orbital strips without crashing system RAM.

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
You will need Python 3.11+ and the [uv package manager](https://github.com/astral-sh/uv) installed on your system.

### 2. Installation
Clone the repository and install dependencies using `uv`:

```bash
git clone https://github.com/AkshatPal2007/LunarCV.git
cd LunarCV

# Create a virtual environment and install all dependencies instantly
uv sync
```

### 3. Running the Pipeline
You can run the primary matching benchmark, which executes LoFTR, LightGlue, and RIFT2 concurrently on the baseline Chandrayaan-2 and LRO image pair:

```bash
uv run python src/matcher_benchmark.py
```

The script will process the multi-gigabyte images, extract features, compute homographies, and save the comparative results to:
- `outputs/metrics/matcher_benchmark.csv`
- `outputs/figures/` (Visual side-by-side overlays and alpha blends)

---

## 📁 Project Structure

```text
LunarCV/
├── data/
│   ├── raw/                 # Place your raw .IMG and .XML satellite data here
│   └── processed/           # Cached features and processed numpy arrays
├── outputs/
│   ├── figures/             # Visualizations (Matches, Overlays, Checkerboards)
│   └── metrics/             # CSV and JSON evaluation reports
└── src/
    ├── config.py            # Global paths, sensor resolutions (GSD), and bounding boxes
    ├── io_utils.py          # Zero-copy memory mapping for massive planetary images
    ├── preprocessing.py     # CLAHE and percentile stretching
    ├── matching.py          # LoFTR Matcher implementation
    ├── matching_lightglue.py# ALIKED + LightGlue implementation
    ├── matching_rift2.py    # RIFT2 Phase-Congruency implementation
    ├── outlier_rejection.py # MAGSAC++ geometry filtering
    └── matcher_benchmark.py # The main execution script
```

---

## 🔬 Scientific Context
*This project actively tackles the problem of non-linear illumination and extreme resolution gaps (~6.15x spatial discrepancy between OHRC and LRO NAC). For a deep dive into the research methodology, refer to the source code documentation and benchmark logs.*
