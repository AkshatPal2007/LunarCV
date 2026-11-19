"""Validated deployment settings; registration parameters live in RegistrationConfig."""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_checkout = Path(__file__).resolve().parents[2]
ROOT = (
    _checkout
    if (_checkout / "backend/pyproject.toml").is_file()
    else Path(os.environ.get("LUNARCV_HOME", str(Path.home() / ".local/share/lunarcv")))
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=(ROOT / ".env", Path.cwd() / ".env"),
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "LunarCV API"
    VERSION: str = "0.3.0"
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]
    MAX_UPLOAD_SIZE: int = 2 * 1024**3
    ALLOWED_EXTENSIONS: set[str] = {".img", ".tif", ".tiff", ".png", ".jpg", ".jpeg"}
    BASE_DIR: Path = ROOT
    RAW_DIR: Path = ROOT / "data/raw"
    UPLOAD_DIR: Path = ROOT / "data/uploads"
    RESULTS_DIR: Path = ROOT / "data/results"
    JOB_DB_PATH: Path = ROOT / "data/jobs.sqlite3"
    CACHE_DIR: Path = ROOT / "outputs/match_cache"
    EVALUATION_MANIFEST_PATH: Path = ROOT / "data/metadata/evaluation_manifest.json"
    CLEANUP_AFTER_HOURS: int = 24
    MAX_PENDING_JOBS: int = Field(4, ge=1, le=16)
    JOB_TIMEOUT_SECONDS: int = Field(600, ge=30)
    API_KEY: str | None = None
    PUBLIC_MODE: bool = False
    MAX_IMAGE_DIMENSION: int = 8192


settings = Settings()
