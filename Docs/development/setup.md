# Development Setup

Guide for setting up a local development environment.

## Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **uv** (recommended) - Fast Python package installer
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Git** - [Download](https://git-scm.com/)
- **Docker** (optional) - [Download](https://www.docker.com/)

## Clone Repository

```bash
git clone <repository-url>
cd LunarCV
```

## Backend Setup

### 1. Install Dependencies

Using `uv` (recommended):
```bash
cd backend
uv sync
```

Using `pip`:
```bash
cd backend
pip install -e .
```

This installs:
- FastAPI and Uvicorn (API server)
- OpenCV, NumPy, PyTorch (CV algorithms)
- Pydantic, Python-multipart (validation, uploads)
- LightGlue (from GitHub)

### 2. Activate Virtual Environment

```bash
# uv creates .venv automatically
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### 3. Run Backend Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the Makefile:
```bash
make dev-backend
```

**Verify:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### 4. Run Tests

```bash
cd backend
pytest
```

### 5. Run Linter

```bash
cd backend
ruff check .
```

Fix automatically:
```bash
ruff check --fix .
```

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This installs:
- React 19
- Vite (build tool)
- Tailwind CSS v4
- Framer Motion (animations)
- Lucide React (icons)

### 2. Configure Environment

Create `frontend/.env`:
```bash
VITE_API_URL=http://localhost:8000/api/v1
```

### 3. Run Frontend Dev Server

```bash
cd frontend
npm run dev
```

Or use the Makefile:
```bash
make dev-frontend
```

**Verify:** http://localhost:5173

### 4. Build for Production

```bash
cd frontend
npm run build
```

Output: `frontend/dist/`

### 5. Run Linter

```bash
cd frontend
npm run lint
```

## Run Both Together

### Option 1: Makefile (Parallel)

```bash
make dev
```

This starts backend and frontend in parallel. Press `Ctrl+C` to stop both.

### Option 2: Docker Compose (Recommended for Consistency)

```bash
make docker-up
```

Stops all services:
```bash
make docker-down
```

## Project Structure

After setup, you should have:

```
LunarCV/
├── backend/
│   ├── .venv/              # Python virtual environment
│   ├── app/                # FastAPI application
│   ├── lunarcv/            # CV library
│   └── pyproject.toml
│
├── frontend/
│   ├── node_modules/       # Node.js dependencies
│   ├── src/                # React source
│   ├── dist/               # Production build
│   └── package.json
│
├── data/
│   ├── uploads/            # User uploads
│   ├── results/            # Job outputs
│   ├── raw/                # Original datasets
│   └── processed/          # Cached features
│
└── docs/                   # Documentation
```

## IDE Configuration

### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance (Microsoft)
- ES7+ React/Redux/React-Native snippets
- Tailwind CSS IntelliSense
- ESLint
- Prettier

Create `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm

1. Open `backend/` as project root
2. Configure Python interpreter: `.venv/bin/python`
3. Enable Ruff plugin
4. Configure code style: PEP 8

## Environment Variables

### Backend (`backend/.env`)

```bash
# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME="LunarCV API"
VERSION=0.1.0

# CORS (comma-separated)
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# File Upload
MAX_UPLOAD_SIZE=1073741824  # 1GB
ALLOWED_EXTENSIONS=.img,.tif,.tiff,.png,.jpg,.jpeg

# Storage Paths (absolute or relative to backend/)
UPLOAD_DIR=../data/uploads
RESULTS_DIR=../data/results

# Processing
CLEANUP_AFTER_HOURS=24
```

### Frontend (`frontend/.env`)

```bash
# API Base URL
VITE_API_URL=http://localhost:8000/api/v1
```

## Database Setup (Future)

Currently, jobs are stored in-memory. For production, set up PostgreSQL or Redis:

```bash
# PostgreSQL
docker run -d \
  --name lunarcv-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=lunarcv \
  -p 5432:5432 \
  postgres:15

# Redis
docker run -d \
  --name lunarcv-redis \
  -p 6379:6379 \
  redis:7-alpine
```

## Troubleshooting

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'lunarcv'`

**Fix:** Install package in editable mode:
```bash
cd backend
pip install -e .
```

**Error:** `torch not found` or CUDA errors

**Fix:** Install PyTorch with CUDA support:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Frontend build fails

**Error:** `npm ERR! code ERESOLVE`

**Fix:** Delete `node_modules` and reinstall:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Port already in use

**Error:** `Address already in use: 8000`

**Fix:** Kill the process:
```bash
# Linux/Mac
lsof -ti:8000 | xargs kill -9

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Docker issues

**Error:** `Cannot connect to Docker daemon`

**Fix:** Start Docker Desktop or Docker service:
```bash
# Linux
sudo systemctl start docker

# Mac
open -a Docker
```

## Next Steps

- [Contributing Guide](contributing.md)
- [Testing Guide](testing.md)
- [Code Style Guide](code-style.md)
