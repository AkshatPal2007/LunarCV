# Configuration Guide

Configure LunarCV for your specific deployment environment.

## Environment Variables

### Backend Configuration

#### API Settings

```bash
# .env or backend/.env

# API Version Prefix
API_V1_STR=/api/v1

# Project Metadata
PROJECT_NAME="LunarCV API"
VERSION=0.1.0
```

#### CORS (Cross-Origin Resource Sharing)

```bash
# Allowed origins (comma-separated, no spaces)
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://lunarcv.example.com

# For development, allow all origins (NOT RECOMMENDED IN PRODUCTION)
# BACKEND_CORS_ORIGINS=*
```

#### File Upload Limits

```bash
# Maximum upload size in bytes (default: 1GB)
MAX_UPLOAD_SIZE=1073741824

# Allowed file extensions (comma-separated)
ALLOWED_EXTENSIONS=.img,.tif,.tiff,.png,.jpg,.jpeg
```

#### Storage Paths

```bash
# Relative to backend/ directory or absolute paths
UPLOAD_DIR=../data/uploads
RESULTS_DIR=../data/results

# Absolute paths (Windows)
# UPLOAD_DIR=C:\LunarCV\data\uploads
# RESULTS_DIR=C:\LunarCV\data\results

# Absolute paths (Linux)
# UPLOAD_DIR=/var/lib/lunarcv/uploads
# RESULTS_DIR=/var/lib/lunarcv/results
```

#### Processing Settings

```bash
# Auto-delete results after N hours (0 = never delete)
CLEANUP_AFTER_HOURS=24

# Maximum concurrent jobs (0 = unlimited)
MAX_CONCURRENT_JOBS=3
```

### Frontend Configuration

```bash
# frontend/.env

# Backend API URL
VITE_API_URL=http://localhost:8000/api/v1

# Production example
# VITE_API_URL=https://api.lunarcv.example.com/api/v1
```

## Configuration Files

### Backend: `backend/app/config.py`

For advanced configuration beyond environment variables:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "LunarCV API"
    
    # CORS - parsed from comma-separated string
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 1024 * 1024 * 1024  # 1GB
    ALLOWED_EXTENSIONS: set = {".img", ".tif", ".tiff", ".png", ".jpg", ".jpeg"}
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    RESULTS_DIR: Path = BASE_DIR / "data" / "results"
    
    # Processing
    CLEANUP_AFTER_HOURS: int = 24
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
```

**To customize:**

1. Edit `backend/app/config.py` directly, OR
2. Set environment variables (they override file values)

### CV Pipeline: `backend/lunarcv/config.py`

Dataset-specific configuration:

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Chandrayaan-2 OHRC
OHRC_SHAPE = (90148, 12000)
OHRC_DTYPE = "uint8"
OHRC_GSD = 0.26  # meters/pixel

# LRO NAC
LRO_SHAPE = (52224, 2532)
LRO_DTYPE = "uint8"
LRO_GSD = 1.60  # meters/pixel

# Scale ratios
SCALE_Y_LRO_TO_OHRC = 15000 / 3294  # ~4.55x
SCALE_X_LRO_TO_OHRC = 6000 / 571    # ~10.5x
```

**To customize:**

Add your own sensor configurations in `lunarcv/config.py`.

## Docker Configuration

### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      # Override any backend env vars here
      - BACKEND_CORS_ORIGINS=http://localhost:5173
      - MAX_UPLOAD_SIZE=2147483648  # 2GB
    volumes:
      - ./data:/app/data
    ports:
      - "8000:8000"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      # Override frontend env vars here
      - VITE_API_URL=http://localhost:8000/api/v1
    ports:
      - "5173:80"
```

### Resource Limits

Add resource constraints for production:

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

## GPU Configuration

### Enable GPU Support (NVIDIA only)

**1. Install nvidia-docker2:**

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

**2. Update docker-compose.yml:**

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

**3. Verify:**

```bash
docker-compose exec backend python -c "import torch; print(torch.cuda.is_available())"
```

Should output: `True`

## Logging Configuration

### Backend Logging

Create `backend/logging_config.yaml`:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    formatter: default
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    formatter: detailed
    filename: logs/lunarcv.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  lunarcv:
    level: INFO
    handlers: [console, file]
    propagate: false
  
  uvicorn:
    level: INFO
    handlers: [console]

root:
  level: WARNING
  handlers: [console]
```

**Load in `backend/app/main.py`:**

```python
import logging.config
import yaml

with open("logging_config.yaml") as f:
    config = yaml.safe_load(f)
    logging.config.dictConfig(config)
```

### Log Levels

Set via environment variable:

```bash
# Development - verbose
LOG_LEVEL=DEBUG

# Production - errors only
LOG_LEVEL=ERROR
```

## Security Configuration

### Production Checklist

- [ ] **Set unique SECRET_KEY** for session signing
- [ ] **Disable debug mode** (`DEBUG=False`)
- [ ] **Restrict CORS origins** (no wildcards)
- [ ] **Enable HTTPS** (use reverse proxy)
- [ ] **Set file size limits** appropriately
- [ ] **Enable authentication** (OAuth2/JWT)
- [ ] **Use environment secrets** (not committed `.env`)

### Secret Management

**Development:** Use `.env` file (in `.gitignore`)

**Production:** Use secret manager:

```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id lunarcv/prod/api-key

# Kubernetes Secret
kubectl create secret generic lunarcv-secrets \
  --from-literal=api-key=your-secret-key
```

## Performance Tuning

### Uvicorn Workers

For production, run multiple workers:

```bash
# backend/Dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Rule of thumb:** `workers = (2 × CPU_cores) + 1`

### Feature Matching

Tune for speed vs accuracy:

```python
# backend/lunarcv/matching/lightglue_matcher.py

# Fast (less accurate)
LightGlueFeatureMatcher(max_dim=1024, max_keypoints=1024)

# Balanced (default)
LightGlueFeatureMatcher(max_dim=1500, max_keypoints=2048)

# Slow (more accurate)
LightGlueFeatureMatcher(max_dim=2048, max_keypoints=4096)
```

### Caching

Add Redis for job result caching (future):

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Troubleshooting

### Environment Variable Not Loading

**Check precedence:**
1. Explicit env var (`export VAR=value`)
2. `.env` file in working directory
3. Default in `config.py`

**Debug:**
```python
from app.config import settings
print(settings.dict())
```

### CORS Errors

**Symptom:** Browser console shows CORS policy errors

**Fix:**
```bash
# Backend .env - Add frontend origin
BACKEND_CORS_ORIGINS=http://localhost:5173,https://yourdomain.com
```

### Path Issues

**Symptom:** Files not found, uploads fail

**Debug:**
```python
from app.config import settings
print(f"Upload dir: {settings.UPLOAD_DIR}")
print(f"Exists: {settings.UPLOAD_DIR.exists()}")
```

**Fix:** Use absolute paths in production:
```bash
UPLOAD_DIR=/var/lib/lunarcv/uploads
RESULTS_DIR=/var/lib/lunarcv/results
```

## Configuration Templates

### Development

`.env`:
```bash
# Development settings
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
MAX_UPLOAD_SIZE=1073741824
CLEANUP_AFTER_HOURS=1
LOG_LEVEL=DEBUG
```

### Production

`.env`:
```bash
# Production settings
BACKEND_CORS_ORIGINS=https://lunarcv.example.com
MAX_UPLOAD_SIZE=2147483648
CLEANUP_AFTER_HOURS=168  # 1 week
LOG_LEVEL=WARNING
SECRET_KEY=<random-secret-from-vault>
```

## Next Steps

- [Development Setup](../development/setup.md)
- [Docker Deployment](../deployment/docker.md)
- [Backend Architecture](../architecture/backend.md)
