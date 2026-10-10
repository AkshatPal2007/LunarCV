"""
FastAPI application entry point for LunarCV.
"""

import logging
import warnings

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.api.routes import health, images, registration, upload
from app.config import settings
from app.exceptions import LunarCVError

logger = logging.getLogger(__name__)

# Suppress torch.jit.script deprecation warning from dependencies
warnings.filterwarnings("ignore", category=FutureWarning, module="torch.jit._script")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler for LunarCV exceptions
@app.exception_handler(LunarCVError)
async def lunarcv_exception_handler(request, exc: LunarCVError):
    """Handle LunarCV exceptions with user-friendly messages."""
    return JSONResponse(status_code=400, content={"detail": exc.user_message})


# Include routers
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(upload.router, prefix=settings.API_V1_STR, tags=["upload"])
app.include_router(images.router, prefix=settings.API_V1_STR, tags=["images"])
app.include_router(
    registration.router, prefix=settings.API_V1_STR, tags=["registration"]
)
from app.api.routes import config
app.include_router(config.router, prefix=settings.API_V1_STR, tags=["config"])


_ALLOWED_RESULT_DIRS = {
    "showcase_submission": settings.BASE_DIR / "outputs" / "submission",
    "showcase_baseline": settings.RESULTS_DIR / "showcase_baseline_run",
    "figures": settings.BASE_DIR / "outputs" / "figures",
}


@app.get(f"{settings.API_V1_STR}/files/{{job_id}}/{{filename}}")
async def get_result_file(job_id: str, filename: str):
    """Serve result files (images, CSV, etc.)."""
    base_dir = _ALLOWED_RESULT_DIRS.get(job_id, settings.RESULTS_DIR / job_id)
    file_path = (base_dir / filename).resolve()

    if not file_path.is_relative_to(base_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "LunarCV API", "version": settings.VERSION, "docs": "/docs"}
