"""
Health check endpoints.
"""

from fastapi import APIRouter

from app.config import settings
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version=settings.VERSION)


@router.get("/ready")
async def readiness():
    import os
    from pathlib import Path

    from fastapi import HTTPException

    from app.jobs import JobRepository

    with JobRepository().connect() as db:
        db.execute("SELECT 1")
    cache_root = Path(
        os.environ.get(
            "TORCH_HOME",
            str(
                Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
                / "torch"
            ),
        )
    )
    assets = cache_root / "hub/checkpoints"
    required = ["aliked-n16.pth", "aliked_lightglue_v0-1_arxiv.pth"]
    missing = [name for name in required if not (assets / name).is_file()]
    if missing:
        raise HTTPException(
            status_code=503,
            detail={
                "missing_model_assets": missing,
                "action": "run scripts/prefetch_models.py",
            },
        )
    return {
        "status": "ready",
        "compute_concurrency": 1,
        "device_detection": "performed by isolated worker at execution",
    }
