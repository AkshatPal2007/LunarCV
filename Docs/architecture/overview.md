# System Architecture Overview

LunarCV is a multi-modal lunar image registration system with a FastAPI backend and React frontend.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                      (React + Vite)                          │
│                                                              │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Upload   │  │ Registration │  │  Visualization   │   │
│  │   UI       │  │   Dashboard  │  │   Components     │   │
│  └────────────┘  └──────────────┘  └──────────────────┘   │
│                          │                                   │
│                    API Client (Axios)                       │
└──────────────────────────┼──────────────────────────────────┘
                           │ HTTP/REST
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                   Backend (FastAPI)                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │             API Routes Layer                          │  │
│  │  /upload  /register  /jobs/{id}  /jobs/{id}/results │  │
│  └─────────────────────┼────────────────────────────────┘  │
│                        │                                     │
│  ┌─────────────────────┼────────────────────────────────┐  │
│  │          Services Layer                              │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │  registration_service.py                    │    │  │
│  │  │  - Job orchestration                        │    │  │
│  │  │  - Background task management               │    │  │
│  │  │  - Progress tracking                        │    │  │
│  │  └─────────────────┼───────────────────────────┘    │  │
│  └────────────────────┼──────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────┼──────────────────────────────────┐ │
│  │         lunarcv Package (CV Pipeline)               │ │
│  │                                                       │ │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │   I/O      │  │  Matching    │  │Registration │ │ │
│  │  │  - Raster  │→ │  - LightGlue │→ │  - MAGSAC++ │ │ │
│  │  │  - Memmap  │  │  - LoFTR     │  │  - Subpixel │ │ │
│  │  └────────────┘  │  - RIFT2     │  │  - Transform│ │ │
│  │                  └──────────────┘  └─────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────┼──────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
            ┌───────▼──────┐ ┌───▼──────┐
            │   Uploads    │ │ Results  │
            │   Storage    │ │ Storage  │
            └──────────────┘ └──────────┘
```

## Component Breakdown

### Frontend (React + Vite)
- **Purpose**: User interface for image upload and registration visualization
- **Tech Stack**: React 19, Vite, Tailwind CSS v4, Framer Motion
- **Key Features**:
  - Drag-and-drop image upload
  - Real-time job progress tracking
  - Interactive result visualization (overlays, checkerboards, match points)
  - Geographic footprint mapping

### Backend (FastAPI)
- **Purpose**: REST API and CV pipeline orchestration
- **Tech Stack**: FastAPI, Uvicorn, Pydantic
- **Layers**:
  1. **API Routes** - HTTP endpoint handlers
  2. **Schemas** - Request/response validation (Pydantic)
  3. **Services** - Business logic and job management
  4. **lunarcv Package** - Core CV algorithms

### CV Pipeline (lunarcv)
Pure Python computer vision library implementing the registration pipeline:

1. **I/O Module** (`lunarcv.io`)
   - Zero-copy memory-mapped loading for large orbital imagery
   - PDS3/PDS4 format support
   - Patch extraction

2. **Preprocessing** (`lunarcv.preprocessing`)
   - Percentile-based normalization
   - CLAHE (optional)

3. **Matching** (`lunarcv.matching`)
   - **LightGlue** - Primary matcher (SuperPoint + LightGlue)
   - **LoFTR** - Dense transformer-based matching
   - **RIFT2** - Phase congruency matcher (illumination-invariant)

4. **Registration** (`lunarcv.registration`)
   - **Outlier Rejection** - MAGSAC++ geometric filtering
   - **Spatial Uniformity** - Grid-based distribution analysis
   - **Sub-pixel Refinement** - cornerSubPix + Lucas-Kanade
   - **Transform Estimation** - Homography/Affine/TPS fitting

## Data Flow

### Registration Job Lifecycle

```
1. Upload Images
   POST /api/v1/upload (source)
   POST /api/v1/upload (reference)
   ↓
2. Create Job
   POST /api/v1/register
   {source_image_id, reference_image_id, matcher}
   ↓
3. Background Processing
   - Load images (cv2.imread or memmap)
   - Normalize (percentile stretch)
   - Feature matching (LightGlue/LoFTR/RIFT2)
   - Outlier rejection (MAGSAC++)
   - Sub-pixel refinement
   - Transform estimation
   - Generate outputs (registered image, overlay, metrics)
   ↓
4. Poll Status
   GET /api/v1/jobs/{job_id}
   {status: "processing", progress: 75}
   ↓
5. Retrieve Results
   GET /api/v1/jobs/{job_id}/results
   {metrics, registered_image_url, overlay_image_url, ...}
```

## Storage Architecture

### Uploads Directory (`data/uploads/`)
- User-uploaded source and reference images
- Files named by UUID
- Original filenames preserved in metadata

### Results Directory (`data/results/{job_id}/`)
Per-job outputs:
- `registered.png` - Warped reference image aligned to source
- `overlay.png` - 50/50 alpha blend of registered pair
- `checkerboard.png` - Checkerboard composite for visual QA
- `correspondence_points.csv` - Match coordinates (source_x, source_y, reference_x, reference_y)
- `metrics.json` - Evaluation metrics (RMSE, inlier ratio, spatial uniformity)

## Scalability Considerations

### Current Implementation (MVP)
- **Job Store**: In-memory dictionary (ephemeral)
- **Storage**: Local filesystem
- **Concurrency**: FastAPI background tasks (single worker)

### Production Recommendations
- **Job Store**: Redis or PostgreSQL for persistence
- **Task Queue**: Celery + Redis for distributed processing
- **Storage**: S3/MinIO for large imagery
- **Caching**: Redis for frequently-accessed results
- **Load Balancing**: Nginx reverse proxy + multiple Uvicorn workers

## Security Notes

- File uploads are validated by extension and size
- No authentication implemented yet (add OAuth2/JWT for production)
- CORS configured for localhost development (restrict in production)
- Job results are publicly accessible by job_id (add user ownership in production)

## Technology Choices

| Component | Technology | Reasoning |
|-----------|-----------|-----------|
| Backend Framework | FastAPI | Fast, async, automatic OpenAPI docs, Pydantic validation |
| CV Library | OpenCV + PyTorch | Industry standard, GPU support, extensive algorithms |
| Feature Matcher | LightGlue | SOTA accuracy, faster than SuperGlue, MIT license |
| Frontend Framework | React 19 | Modern, component-based, large ecosystem |
| Build Tool | Vite | Fast HMR, optimized builds, ESM native |
| Containerization | Docker | Reproducible environments, easy deployment |

## Next Steps

- [Backend Architecture Details](backend.md)
- [CV Pipeline Deep Dive](cv-pipeline.md)
- [Frontend Architecture](frontend.md)
