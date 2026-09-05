# LunarCV Backend

FastAPI backend for the LunarCV multi-modal lunar image registration system.

## Structure

```
backend/
├── app/                          # FastAPI application
│   ├── api/
│   │   └── routes/              # API endpoints
│   │       ├── health.py        # Health check
│   │       ├── upload.py        # Image upload
│   │       └── registration.py  # Registration jobs
│   ├── schemas/                 # Pydantic models
│   ├── services/                # Business logic
│   │   └── registration_service.py
│   ├── config.py                # API configuration
│   └── main.py                  # FastAPI app entry point
│
├── lunarcv/                     # Core CV library
│   ├── io/                      # Memory-mapped I/O
│   ├── preprocessing/           # Image normalization
│   ├── matching/                # Feature matchers (LightGlue, etc.)
│   ├── registration/            # Outlier rejection, transform
│   └── config.py                # CV pipeline config
│
└── scripts/
    └── register_pair.py         # CLI registration tool
```

## Installation

From the `backend/` directory:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Running the API Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API documentation: http://localhost:8000/docs

## API Endpoints

### Upload Images
```bash
POST /api/v1/upload
```
Upload source or reference image (supports .img, .tif, .png, .jpg)

### Start Registration Job
```bash
POST /api/v1/register
Body: {
  "source_image_id": "uuid-from-upload",
  "reference_image_id": "uuid-from-upload",
  "matcher": "lightglue"
}
```

### Check Job Status
```bash
GET /api/v1/jobs/{job_id}
```

### Get Results
```bash
GET /api/v1/jobs/{job_id}/results
```

Returns metrics, registered image, overlay, checkerboard, and correspondence CSV.

## CLI Usage

Run registration from command line:

```bash
cd backend
python -m scripts.register_pair
```

## Development

```bash
# Run linter
ruff check .

# Format code
ruff format .

# Run tests
pytest
```
