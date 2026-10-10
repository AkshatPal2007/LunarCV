# LunarCV Backend

The backend provides the FastAPI application and the maintained Python image
registration library.

## Components

- `app/`: API routes, Pydantic schemas, upload validation, and registration
  services.
- `lunarcv/`: image I/O, geographic priors, normalization, LightGlue/RIFT2
  matching, MAGSAC++ filtering, spatial-uniformity metrics, sub-pixel
  refinement, and transform/warp utilities.
- `scripts/register_pair.py`: real-data batch registration entry point.
- `tests/`: backend-focused tests for evaluation metadata and manifest logic.

## Setup

From the repository root:

```bash
cd backend
uv sync
```

The project requires Python 3.11 or newer. `uv.lock` records the resolved
backend environment.

## Run the API

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI documentation is served at `http://localhost:8000/docs`. The API
prefix is `/api/v1`.

Implemented operations include:

- `GET /health`
- `POST /upload`
- `GET /images`
- `POST /register`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/results`
- `GET /config/correspondence-points`
- `GET /config/transform-matrix`
- `GET /config/processing`

## Batch Registration

The batch script expects the real OHRC image, calibrated OHRC geometry CSV,
and LRO NAC image configured in `lunarcv/config.py`:

```bash
cd backend
uv run python scripts/register_pair.py
```

Full-resolution runs can be resource intensive. They write generated products
to local output directories that are ignored by Git.

## Tests and Checks

```bash
cd backend
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The repository also contains legacy top-level tests for standalone helpers in
`../src`; those are outside this backend package's pytest configuration.
