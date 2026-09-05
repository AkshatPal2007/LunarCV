"""
FastAPI application entry point for LunarCV.
"""

import warnings

# Suppress torch.jit.script deprecation warning from dependencies
warnings.filterwarnings("ignore", category=FutureWarning, module="torch.jit._script")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.routes import health, upload, registration

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

# Include routers
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(upload.router, prefix=settings.API_V1_STR, tags=["upload"])
app.include_router(
    registration.router, prefix=settings.API_V1_STR, tags=["registration"]
)


# Serve result files
@app.get(f"{settings.API_V1_STR}/files/{{job_id}}/{{filename}}")
async def get_result_file(job_id: str, filename: str):
    """Serve result files (images, CSV, etc.)."""
    file_path = settings.RESULTS_DIR / job_id / filename

    if not file_path.exists():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "LunarCV API", "version": settings.VERSION, "docs": "/docs"}
