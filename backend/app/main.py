"""
FastAPI application entry point for LunarCV.
"""

import warnings

# Suppress torch.jit.script deprecation warning from dependencies
warnings.filterwarnings("ignore", category=FutureWarning, module="torch.jit._script")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, images, registration, upload
from app.config import settings
from app.exceptions import LunarCVException

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
@app.exception_handler(LunarCVException)
async def lunarcv_exception_handler(request, exc: LunarCVException):
    """Handle LunarCV exceptions with user-friendly messages."""
    return JSONResponse(status_code=400, content={"detail": exc.user_message})


# Include routers
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(upload.router, prefix=settings.API_V1_STR, tags=["upload"])
app.include_router(images.router, prefix=settings.API_V1_STR, tags=["images"])
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
