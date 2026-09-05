# Quick Start Guide

Get LunarCV running in 5 minutes using Docker.

## Prerequisites

- Docker and docker-compose installed
- Git (to clone the repository)

## Steps

### 1. Clone and Setup

```bash
git clone <repository-url>
cd LunarCV
cp .env.example .env
```

### 2. Start with Docker

```bash
make docker-up
```

This starts both backend and frontend services.

### 3. Access the Application

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173

### 4. Test the API

Upload a test image:

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@path/to/source.png"
```

Response:
```json
{
  "file_id": "uuid-here",
  "filename": "source.png",
  "size": 1024000,
  "uploaded_at": "2026-09-06T00:00:00"
}
```

Start a registration job:

```bash
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "source_image_id": "source-uuid",
    "reference_image_id": "reference-uuid",
    "matcher": "lightglue"
  }'
```

### 5. View Results

Check job status:
```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

Get results when complete:
```bash
curl http://localhost:8000/api/v1/jobs/{job_id}/results
```

## Alternative: Local Development

Without Docker:

```bash
# Install dependencies
make install

# Run backend + frontend
make dev
```

## Next Steps

- Read the [API documentation](api/endpoints.md)
- Explore the [CV pipeline](architecture/cv-pipeline.md)
- Check [development setup](development/setup.md) for contributing

## Troubleshooting

**Port already in use:**
```bash
make docker-down
make docker-up
```

**Permission errors:**
```bash
sudo make docker-up
```

**View logs:**
```bash
make docker-logs
```
