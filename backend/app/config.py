"""
FastAPI application configuration.
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "LunarCV API"
    VERSION: str = "0.1.0"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
    ]

    # File Upload
    MAX_UPLOAD_SIZE: int = 1024 * 1024 * 1024  # 1GB
    ALLOWED_EXTENSIONS: set = {".img", ".tif", ".tiff", ".png", ".jpg", ".jpeg"}

    # Storage paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    RESULTS_DIR: Path = BASE_DIR / "data" / "results"

    # Processing
    CLEANUP_AFTER_HOURS: int = 24  # Auto-delete results after 24 hours

    class Config:
        case_sensitive = True


settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
