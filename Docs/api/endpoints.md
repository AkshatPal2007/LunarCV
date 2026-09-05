# API Reference

Complete reference for the LunarCV REST API.

## Base URL

```
http://localhost:8000/api/v1
```

## Endpoints

### Health Check

#### GET /health

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

**Status Codes:**
- `200 OK` - Service is healthy

---

### Upload Image

#### POST /upload

Upload a source or reference image for registration.

**Request:**
- **Content-Type**: `multipart/form-data`
- **Body**: Form field `file` with image data

**Supported Formats:**
- `.img` (PDS raw)
- `.tif`, `.tiff` (GeoTIFF)
- `.png`, `.jpg`, `.jpeg`

**Size Limit:** 1GB

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@chandrayaan2_ohrc.png"
```

**Response:**
```json
{
  "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "chandrayaan2_ohrc.png",
  "size": 15728640,
  "uploaded_at": "2026-09-06T12:34:56.789Z"
}
```

**Status Codes:**
- `200 OK` - Upload successful
- `400 Bad Request` - Invalid file type
- `413 Payload Too Large` - File exceeds size limit

---

### Create Registration Job

#### POST /register

Start a registration job between two uploaded images.

**Request:**
```json
{
  "source_image_id": "uuid-of-source-image",
  "reference_image_id": "uuid-of-reference-image",
  "matcher": "lightglue"
}
```

**Parameters:**
- `source_image_id` (string, required) - UUID from upload response
- `reference_image_id` (string, required) - UUID from upload response
- `matcher` (string, optional) - Feature matcher to use
  - `"lightglue"` (default) - SuperPoint + LightGlue
  - `"loftr"` - LoFTR (future)
  - `"rift2"` - RIFT2 (future)

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "source_image_id": "source-uuid",
    "reference_image_id": "reference-uuid",
    "matcher": "lightglue"
  }'
```

**Response:**
```json
{
  "job_id": "job-uuid",
  "status": "pending",
  "created_at": "2026-09-06T12:35:00.000Z"
}
```

**Status Codes:**
- `200 OK` - Job created successfully
- `404 Not Found` - Source or reference image not found

---

### Get Job Status

#### GET /jobs/{job_id}

Poll the status of a registration job.

**Parameters:**
- `job_id` (path, string) - UUID of the job

**Example:**
```bash
curl http://localhost:8000/api/v1/jobs/job-uuid
```

**Response:**
```json
{
  "job_id": "job-uuid",
  "status": "processing",
  "progress": 75,
  "message": "Refining matches...",
  "created_at": "2026-09-06T12:35:00.000Z",
  "completed_at": null
}
```

**Status Values:**
- `pending` - Job queued, not started
- `processing` - Job in progress
- `completed` - Job finished successfully
- `failed` - Job failed

**Progress:** 0-100 integer (only present during `processing`)

**Status Codes:**
- `200 OK` - Job found
- `404 Not Found` - Job does not exist

---

### Get Job Results

#### GET /jobs/{job_id}/results

Retrieve results from a completed job.

**Parameters:**
- `job_id` (path, string) - UUID of the job

**Example:**
```bash
curl http://localhost:8000/api/v1/jobs/job-uuid/results
```

**Response (Success):**
```json
{
  "job_id": "job-uuid",
  "status": "completed",
  "metrics": {
    "candidate_matches": 1234,
    "inlier_matches": 987,
    "inlier_ratio": 0.800,
    "reprojection_rmse_px": 0.62,
    "median_error_px": 0.45,
    "max_error_px": 2.31,
    "mean_displacement_px": 0.12,
    "spatial_uniformity": {
      "grid_occupancy_pct": 93.75,
      "convex_hull_coverage_pct": 87.2,
      "min_point_separation_px": 15.4
    }
  },
  "registered_image_url": "/api/v1/files/job-uuid/registered.png",
  "overlay_image_url": "/api/v1/files/job-uuid/overlay.png",
  "checkerboard_image_url": "/api/v1/files/job-uuid/checkerboard.png",
  "correspondence_csv_url": "/api/v1/files/job-uuid/correspondence_points.csv",
  "error": null
}
```

**Response (Failed):**
```json
{
  "job_id": "job-uuid",
  "status": "failed",
  "metrics": null,
  "registered_image_url": null,
  "overlay_image_url": null,
  "checkerboard_image_url": null,
  "correspondence_csv_url": null,
  "error": "Insufficient inliers found"
}
```

**Status Codes:**
- `200 OK` - Job completed (check `status` field)
- `400 Bad Request` - Job not ready (still processing)
- `404 Not Found` - Job does not exist

---

### Get Result File

#### GET /files/{job_id}/{filename}

Download a specific result file.

**Parameters:**
- `job_id` (path, string) - UUID of the job
- `filename` (path, string) - File to download
  - `registered.png`
  - `overlay.png`
  - `checkerboard.png`
  - `correspondence_points.csv`
  - `metrics.json`

**Example:**
```bash
curl http://localhost:8000/api/v1/files/job-uuid/registered.png \
  --output registered.png
```

**Response:** Binary file content

**Status Codes:**
- `200 OK` - File found
- `404 Not Found` - File does not exist

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

**Common Error Codes:**
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `413 Payload Too Large` - Upload exceeds size limit
- `500 Internal Server Error` - Server-side error

---

## Rate Limiting

Currently no rate limiting is implemented. For production, recommend:
- 100 requests/minute per IP for uploads
- 1000 requests/minute per IP for status polling

---

## CORS

CORS is configured for:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (Alternative frontend port)

Update `backend/app/config.py` to add additional origins.

---

## Future Endpoints (Planned)

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/logout` - User logout

### User Management
- `GET /users/me` - Get current user
- `GET /users/me/jobs` - List user's jobs

### Advanced Features
- `WS /jobs/{job_id}/stream` - WebSocket for real-time progress
- `DELETE /jobs/{job_id}` - Cancel a running job
- `POST /register/batch` - Batch registration jobs
