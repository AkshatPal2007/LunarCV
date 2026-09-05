# Docker Deployment Guide

Deploy LunarCV using Docker and docker-compose for consistent, reproducible environments.

## Prerequisites

- Docker 20.10+ ([Install](https://docs.docker.com/get-docker/))
- docker-compose 2.0+ (bundled with Docker Desktop)

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd LunarCV
cp .env.example .env
```

Edit `.env` if needed (defaults work for local development).

### 2. Start Services

```bash
make docker-up
```

Or manually:
```bash
docker-compose up -d
```

### 3. Verify Services

- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

Check logs:
```bash
make docker-logs
```

Or:
```bash
docker-compose logs -f
```

### 4. Stop Services

```bash
make docker-down
```

Remove volumes too:
```bash
make docker-down-volumes
```

## Development vs Production

### Development Mode (`docker-compose.dev.yml`)

- **Hot reload** - Code changes reflected immediately
- **Volume mounts** - Local files mounted into containers
- **Debug-friendly** - Full logs, no optimizations

**Start:**
```bash
docker-compose -f docker-compose.dev.yml up
```

**Features:**
- Backend uses `uvicorn --reload`
- Frontend runs Vite dev server with HMR
- Volumes: `./backend:/app`, `./frontend:/app`
- Environment variables from `.env`

### Production Mode (`docker-compose.yml`)

- **Optimized builds** - Production-ready images
- **No mounts** - Code baked into images
- **Nginx** - Serves frontend static files

**Start:**
```bash
docker-compose up -d
```

**Features:**
- Backend runs standard uvicorn
- Frontend built and served via nginx
- Named volumes for persistence
- CORS configured for production domains

## Architecture

```
┌─────────────────────────────────────────┐
│     Docker Host                         │
│                                         │
│  ┌─────────────┐      ┌──────────────┐│
│  │  Frontend   │      │   Backend    ││
│  │  Container  │◄────►│   Container  ││
│  │  Port: 5173 │      │   Port: 8000 ││
│  └─────────────┘      └──────────────┘│
│         │                     │        │
│         └─────────┬───────────┘        │
│                   │                    │
│            ┌──────▼──────┐            │
│            │   Volumes   │            │
│            │  - uploads  │            │
│            │  - results  │            │
│            └─────────────┘            │
└─────────────────────────────────────────┘
```

## Dockerfile Details

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git build-essential

# Install uv for faster deps
RUN pip install uv

# Copy and install dependencies
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

# Copy application
COPY . .

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Image size:** ~1.2 GB (includes PyTorch, OpenCV)

### Frontend Dockerfile

**Production (multi-stage):**
```dockerfile
# Stage 1: Build
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

**Image size:** ~25 MB (nginx + static files)

**Development:**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

## Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins (comma-separated) |
| `MAX_UPLOAD_SIZE` | `1073741824` | Max file size (1GB) |
| `CLEANUP_AFTER_HOURS` | `24` | Auto-delete results after N hours |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Backend API base URL |

## Persistent Volumes

### Named Volumes (Production)

```yaml
volumes:
  backend-venv:    # Python virtual environment
  data-uploads:    # User-uploaded images
  data-results:    # Job outputs
```

**Backup volumes:**
```bash
docker run --rm -v lunarcv_data-uploads:/data -v $(pwd):/backup ubuntu tar cvf /backup/uploads.tar /data
```

**Restore volumes:**
```bash
docker run --rm -v lunarcv_data-uploads:/data -v $(pwd):/backup ubuntu tar xvf /backup/uploads.tar -C /
```

### Bind Mounts (Development)

Development mode mounts local directories:
- `./backend` → `/app` (backend container)
- `./frontend` → `/app` (frontend container)
- `./data` → `/app/data` (shared)

Changes on host immediately reflected in containers.

## Networking

Containers communicate via internal `lunarcv-network`:

```yaml
networks:
  lunarcv-network:
    driver: bridge
```

Frontend calls backend via:
- Internal: `http://backend:8000`
- External: `http://localhost:8000`

## Resource Limits

Add resource constraints in production:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

Recommended minimums:
- Backend: 2 CPU, 4GB RAM (for LightGlue inference)
- Frontend: 0.5 CPU, 512MB RAM

## Health Checks

Add health checks to docker-compose.yml:

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Check status:
```bash
docker-compose ps
```

## Troubleshooting

### Backend won't start

**Error:** `ModuleNotFoundError`

**Fix:** Rebuild with `--no-cache`:
```bash
docker-compose build --no-cache backend
docker-compose up backend
```

### Frontend build fails

**Error:** `npm ERR! code ELIFECYCLE`

**Fix:** Clear node_modules and rebuild:
```bash
docker-compose down
docker-compose build --no-cache frontend
docker-compose up frontend
```

### Port conflicts

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Fix:** Change ports in docker-compose.yml:
```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Host:Container
```

### GPU not accessible

**Error:** LightGlue falls back to CPU

**Fix:** Enable GPU passthrough (NVIDIA only):

```yaml
services:
  backend:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Requires `nvidia-docker2` on host.

### Volume permissions

**Error:** Permission denied writing to `/app/data`

**Fix:** Set correct ownership:
```bash
docker-compose exec backend chown -R $(id -u):$(id -g) /app/data
```

## Production Deployment

### Checklist

- [ ] Set strong secrets in `.env`
- [ ] Configure CORS for production domains
- [ ] Enable HTTPS (reverse proxy)
- [ ] Set up log aggregation
- [ ] Configure monitoring
- [ ] Enable automatic restarts (`restart: unless-stopped`)
- [ ] Limit resource usage
- [ ] Set up backups for volumes
- [ ] Use tagged images (not `:latest`)

### Reverse Proxy (nginx)

```nginx
server {
    listen 80;
    server_name lunarcv.example.com;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### SSL with Let's Encrypt

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d lunarcv.example.com
```

## Docker Compose Reference

### Build from source

```bash
docker-compose build
```

### Force recreate containers

```bash
docker-compose up --force-recreate
```

### Scale services

```bash
docker-compose up --scale backend=3
```

Requires removing port mappings (use load balancer instead).

### View resource usage

```bash
docker stats
```

### Clean up

```bash
# Stop and remove containers, networks
docker-compose down

# Also remove volumes
docker-compose down -v

# Remove images too
docker-compose down --rmi all -v

# Clean system-wide
docker system prune -a --volumes
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build images
        run: docker-compose build
      - name: Push to registry
        run: |
          docker tag lunarcv-backend registry.example.com/lunarcv-backend:${{ github.sha }}
          docker push registry.example.com/lunarcv-backend:${{ github.sha }}
```

## Next Steps

- [Production Setup](production.md)
- [Monitoring Guide](monitoring.md)
- [Backend Architecture](../architecture/backend.md)
