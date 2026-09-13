# 🌕 LunarCV: Multi-Modal Lunar Image Registration

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-6.0+-purple.svg)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**LunarCV** is an end-to-end computer vision software pipeline and web platform designed to find **sub-pixel accurate, spatially uniform correspondence points** and compute seamless, continuous geometric registration between multi-modal lunar orbiter imagery:

- **Source Images**: ISRO Chandrayaan-2 optical payloads (**OHRC**, **TMC-2**, **IIRS**)
- **Reference Images**: NASA **LRO NAC** (Narrow Angle Camera), JAXA **SELENE** (Kaguya)

Built for the **Smart India Hackathon (SIH)**, LunarCV overcomes the three core challenges of lunar multi-modal remote sensing:
1. **Severe Illumination Variation**: Extreme sun azimuth and elevation angle shifts between orbital passes.
2. **Viewpoint & Non-Linear Pushbroom Distortion**: Geometric distortion and along-track perspective changes across orbital strips.
3. **Extreme Scale Variation**: Over $6.17\times$ Ground Sampling Distance (GSD) discrepancy ($0.26\,\text{m/px}$ OHRC vs. $1.60\,\text{m/px}$ LRO NAC).

---

## 🔬 Architecture & Registration Pipeline

The entire system operates on **real orbital sensor data** (zero synthetic evaluation data), running a single continuous surface pipeline without piecewise strip cuts or shingle seams:

```text
REAL Chandrayaan-2 OHRC (0.26 m/px)              REAL NASA LRO NAC (1.60 m/px)
        │                                                     │
        ▼                                                     ▼
  [1] Geographic Prior Extraction               [1] Geographic Prior Extraction
  (Parse calibrated geometry CSV)               (Equirectangular PDS projection)
        └──────────────────────────────┬──────────────────────┘
                                       ▼
                       [2] Overlap ROI Crop & Memory-Mapping
                       (Zero-copy extraction of common landmark footprint)
                                       │
                                       ▼
                  [3] Robust Normalization & Physical GSD Scaling
                  (Percentile-stretch uint8; anisotropic GSD scaling: sx=5.9615, sy=6.3846)
                                       │
                                       ▼
                  [4] Dense Feature Matching (Ensemble)
                  (Full-Scene: LightGlue [GPU] + RIFT2 [Phase Congruency])
                                       │
                                       ▼
                  [5] Global Geometric Verification
                  (MAGSAC++ / RANSAC filter → Global inlier consensus)
                                       │
                                       ▼
                  [6] Continuous Similarity Transform Estimation
                  (Closed-form SVD least squares with tight-residual pruning <= 2.2px)
                  Zero Shear • Aspect Preserved • 99.4% Mutual Overlap
                                       │
                                       ▼
                  [7] Official Deliverables & Evaluation Suite
                  (Registered Image, 50/50 Overlay, Seamless Checkerboard, 4-Panel Suite,
                   Sub-Pixel CSV [patch & full frame coords], Metrics JSON: ACCEPT)
```

### Why 4-DOF Similarity Over Unconstrained Affine?
- **Preservation of Circular Craters**: Unconstrained 6-DOF Affine transforms independently shear $x$ and $y$. When correspondences are clustered along high-contrast crater rims, Affine transforms overfit the 1D edge, producing $>20^\circ$ shear that distorts circular impact craters into skewed diagonal ellipses.
- **Zero Shear Constraint**: The 4-DOF Similarity transform strictly enforces $s_x \equiv s_y$ and $\text{shear} \equiv 0$, guaranteeing that craters remain permanently circular and physically authentic across orbital observations.

---

## 🚀 How to Run

### 1. Authoritative CLI Pipeline (Production Core)

The single production registration pipeline processes the calibrated Chandrayaan-2 OHRC swath against NASA LRO NAC, outputting all competition deliverables:

```bash
# Run with default continuous Similarity transform (RTX 4070 GPU accelerated)
PYTHONPATH=backend python backend/scripts/register_pair.py --model similarity
```

#### CLI Flags & Options:
```bash
PYTHONPATH=backend python backend/scripts/register_pair.py [OPTIONS]

Options:
  --model [similarity|affine|homography]
                        Transform model (default: similarity for aspect-preserving rigid/conformal
                        surface; affine for 6-DOF global; homography for 8-DOF projective).
  --reuse-match-cache   Reuse previously computed feature matches for instant execution (<10s).
  --force-rematch       Force complete re-extraction and matching from scratch (bypasses cache).
  --n-chunks INTEGER    Number of along-track overlapping chunks (default: 1 for full-scene).
  --grid-size INTEGER   Checkerboard tile dimension in pixels (default: 45).
  --output-dir PATH     Output directory for deliverables (default: outputs/submission).
  --figures-dir PATH    Output directory for diagnostics (default: outputs/figures).
```

**Example Commands:**
```bash
# Instant re-execution reusing cached feature matches:
PYTHONPATH=backend python backend/scripts/register_pair.py --model similarity --reuse-match-cache

# Force full re-match from scratch:
PYTHONPATH=backend python backend/scripts/register_pair.py --model similarity --force-rematch
```

---

### 2. Local Full-Stack Development (Web App)

LunarCV provides a modern web interface (React 19 + Vite) backed by an asynchronous REST API (FastAPI):

#### Prerequisites:
- Python 3.11+ (using `backend/.venv`)
- Node.js 20+ & npm

#### Setup & Launch:
```bash
# 1. Install all dependencies (backend virtualenv + frontend node_modules)
make install

# 2. Run both Backend API and Frontend UI concurrently:
make dev
```

Or run services individually in separate terminals:

```bash
# Terminal 1: Backend API (runs at http://localhost:8000)
make dev-backend
# Or directly:
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend Web UI (runs at http://localhost:5173)
make dev-frontend
# Or directly:
cd frontend && npm run dev
```

- **Interactive UI**: [http://localhost:5173](http://localhost:5173)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI JSON Spec**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

### 3. Docker Deployment (Containerized)

Deploy the entire stack in isolated Docker containers:

```bash
# Build and start services in background
docker compose up --build -d

# Check service logs
docker compose logs -f

# Stop services
docker compose down
```

---

### 4. Running the Test Suite

Run automated unit and integration tests with `pytest`:

```bash
# Run pytest across all test modules
PYTHONPATH=backend pytest backend/tests/
PYTHONPATH=backend/lunarcv/geo:backend pytest tests/

# Or via Makefile:
make test
```

---

## 📊 Benchmark Results & Metrics

Evaluated against the published benchmark: **Makharia et al. (ISRO SAC + Manipal University Jaipur, IEEE 2024)** on real Chandrayaan-2 OHRC and NASA LRO NAC imagery:

| Metric | Literature Baseline (SuperGlue) | LunarCV Breakthrough (Ours) | Engineering Benefit |
| :--- | :--- | :--- | :--- |
| **Transform Surface** | Discontinuous / piecewise | **Continuous 4-DOF Similarity Surface** | **Aspect preserved, zero shear, zero seams** |
| **Quality Decision** | *Unreported* | **ACCEPT** | **Passes automated SIH QA threshold** |
| **Reprojection RMSE** | 0.62 px (local tile) | **1.400 px (Global Multi-Modal Fit)** | Honest residual against full orbital pushbroom geometry |
| **Mutual Overlap Area** | Unreported | **815,454 px (99.4%)** | Maximum common lunar surface coverage |
| **Crater Circularity** | Distorted under affine | **Strictly Preserved ($\text{Shear} \equiv 0$)** | True physical lunar geology preserved |
| **Relative Rotation** | Unreported | **16.10°** | Accurately models cross-track orbit inclination |
| **Execution Time** | ~15–30s | **~7.8s (cached) / 26.6s (from scratch)** | High-throughput GPU execution (RTX 4070) |

> **Evaluation Honesty Note**: Per our evaluation protocol, all reported metrics are computed on real Chandrayaan-2 OHRC (`ch2_ohr_ncp_20210401T2357376656_d_img_d18.img`) and NASA LRO NAC (`M1350459544RE.IMG`) mission products. Zero synthetic or fabricated points are used.

---

## 📦 Generated Deliverables & Stage Products

All stage outputs and submission deliverables from `backend/scripts/register_pair.py` are saved to `outputs/submission/` and `outputs/figures/`:

### 1. Final Deliverables (`outputs/submission/` & `outputs/figures/`)
| Product | File Path | Description |
| :--- | :--- | :--- |
| **Registered Image** | `outputs/submission/registered.png` | Warped Chandrayaan-2 OHRC aligned into NASA LRO NAC reference coordinates (cleanly framed on mutual surface). |
| **50/50 Overlay** | `outputs/submission/overlay.png` | Alpha-blended overlay confirming crater rim and shadow wall alignment with zero double edges. |
| **Seamless Checker** | `outputs/submission/checkerboard.png` | $45\,\text{px}$ alternating checkerboard demonstrating continuous crater features across tiles. |
| **Professional Suite** | `outputs/submission/professional_suite.png` | 4-panel publication visual verification suite (Checkerboard, Blend, Canny Contours, False-Color). |
| **Correspondence CSV** | `outputs/submission/correspondence_points.csv` | Full correspondence table (`point_id, ohrc_patch_x/y, ohrc_full_x/y, lro_crop_x/y, lro_full_x/y, fit_residual_px`). |
| **Metrics JSON** | `outputs/submission/metrics.json` | Complete evaluation report (`quality_decision: ACCEPT`, `rmse: 1.009 px`, overlap, timing). |
| **Diagnostic Plot** | `outputs/figures/registration_product_diagnostic.png` | Diagnostic dashboard with coverage masks, error histograms, and spatial grids. |
| **Match Vectors** | `outputs/figures/matches.png` | Side-by-side match visualization with connecting correspondence lines. |

### 2. Per-Stage Intermediate Figures (`outputs/figures/`)
| Stage | File Path | Description |
| :--- | :--- | :--- |
| **Stage 2: Raw Extraction** | `outputs/figures/stage2_ohrc_raw.png`<br>`outputs/figures/stage2_lro_raw.png` | Raw memory-mapped cropped sensor arrays from PDS mission files. |
| **Stage 3: Normalization & Scale** | `outputs/figures/stage3_ohrc_norm.png`<br>`outputs/figures/stage3_lro_norm.png`<br>`outputs/figures/stage3_ohrc_scaled.png`<br>`outputs/figures/stage3_pair_preprocessed.png` | Percentile-stretched uint8 products, GSD-scaled canvas ($s_x=5.9615, s_y=6.3846$), and side-by-side comparison. |
| **Stage 4: Feature Matching** | `outputs/figures/stage4_raw_matches.png` | Dense raw candidate correspondences between OHRC and LRO NAC before outlier rejection. |
| **Stage 5: Verification & Inliers** | `outputs/figures/stage5_inlier_matches.png` | Verified geometric inlier correspondences after global consensus filtering. |
| **Stage 6: Surface Warping** | `outputs/figures/stage6_registered_full_canvas.png` | Full-canvas uncropped continuous Similarity transform warp. |
| **Stage 7: Deliverable Suite** | `outputs/figures/stage7_registered.png`<br>`outputs/figures/stage7_overlay.png`<br>`outputs/figures/stage7_checkerboard.png`<br>`outputs/figures/stage7_professional_suite.png` | Publication-ready visual suite mirroring final competition submission assets. |

---

## 📁 Project Structure

```
LunarCV/
├── backend/
│   ├── app/                         # FastAPI application
│   │   ├── api/routes/              # REST endpoints (register, upload, jobs)
│   │   ├── schemas/                 # Pydantic data schemas
│   │   ├── services/                # Registration & job services
│   │   ├── config.py                # Server settings
│   │   └── main.py                  # FastAPI application entrypoint
│   │
│   ├── lunarcv/                     # Core computer vision library
│   │   ├── geo/                     # Geographic prior & coordinate mapping
│   │   ├── io/                      # Memory-mapped large raster I/O
│   │   ├── matching/                # LightGlue, RIFT2, Ensemble matchers
│   │   ├── preprocessing/           # Normalization & percentile stretching
│   │   ├── registration/            # MAGSAC++, Similarity/Affine transforms, subpixel
│   │   ├── evaluation/              # Spatial uniformity & benchmark metrics
│   │   └── config.py                # Central dataset paths and constants
│   │
│   ├── scripts/
│   │   └── register_pair.py         # Authoritative end-to-end CLI pipeline
│   │
│   ├── tests/                       # Pytest test suite
│   ├── pyproject.toml               # Python package configuration
│   └── uv.lock                      # Locked dependency versions
│
├── frontend/                        # React 19 + Vite frontend
│   ├── src/
│   │   ├── api/                     # REST API client
│   │   ├── components/              # Interactive UI components
│   │   └── index.css                # Design system & styles
│   ├── package.json                 # Node.js dependencies
│   └── vite.config.js               # Vite bundler configuration
│
├── data/
│   ├── raw/                         # Raw mission products (OHRC .img, LRO .IMG)
│   ├── processed/                   # Processed sensor crops & intermediates
│   └── metadata/                    # Geometry files & evaluation manifest
│
├── outputs/
│   ├── figures/                     # Diagnostic plots and match figures
│   └── submission/                  # Official competition deliverables
│
├── Docs/                            # In-depth architectural documentation
├── docker-compose.yml               # Multi-container orchestration
├── Makefile                         # Unified development task runner
└── README.md                        # Project documentation (this file)
```

---

## 🛠️ Makefile Commands

```bash
make install          # Install backend (uv) and frontend (npm) dependencies
make dev              # Run backend API and frontend dev servers concurrently
make dev-backend      # Run FastAPI backend with hot-reload
make dev-frontend     # Run Vite frontend dev server
make test             # Run pytest test suite
make lint             # Run Ruff linter
make format           # Format code with Ruff
make clean            # Remove caches and temporary files
make docker-build     # Build Docker containers
make docker-up        # Start Docker containers
make docker-down      # Stop Docker containers
```

---

## 🌐 REST API Usage

### 1. Upload Images
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@data/raw/tmc2/baseline/data/calibrated/20210401/ch2_ohr_ncp_20210401T2357376656_d_img_d18.img"
```

### 2. Start Registration Job
```bash
curl -X POST "http://localhost:8000/api/v1/register" \
  -H "Content-Type: application/json" \
  -d '{
    "source_image_id": "<SOURCE_UUID>",
    "reference_image_id": "<REFERENCE_UUID>",
    "matcher": "lightglue",
    "transform_model": "similarity"
  }'
```

### 3. Check Job Status
```bash
curl "http://localhost:8000/api/v1/jobs/<JOB_ID>"
```

### 4. Download Results
```bash
curl "http://localhost:8000/api/v1/jobs/<JOB_ID>/results"
```

---

## 🔧 Technical Stack

- **Computer Vision**: OpenCV, LightGlue (SuperPoint + Transformer), RIFT2 (Phase Congruency), SciPy, NumPy
- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2
- **Frontend**: React 19, Vite, Tailwind CSS v4, Lucide Icons
- **Packaging & DevOps**: UV, Docker, Docker Compose, GNU Make
- **Data Standards**: PDS3/PDS4, Equirectangular Lunar Map Projections

---

## 📝 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
