"""
Image upload endpoints.
"""

import logging
import uuid
from datetime import datetime, UTC
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.schemas.registration import UploadResponse
from app.services.validation_service import validate_uploaded_file

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload a source or reference image for registration.

    Supports: .img, .tif, .tiff, .png, .jpg, .jpeg
    Max size: 1GB
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    # Generate unique file ID
    file_id = str(uuid.uuid4())
    save_path = settings.UPLOAD_DIR / f"{file_id}{file_ext}"

    # Stream file to disk while enforcing max size
    bytes_read = 0
    with open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            bytes_read += len(chunk)
            if bytes_read > settings.MAX_UPLOAD_SIZE:
                save_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
                )
            f.write(chunk)

    # Validate uploaded file
    validation = validate_uploaded_file(save_path, max_size_mb=1024)
    if not validation["valid"]:
        save_path.unlink()  # Delete invalid file
        raise HTTPException(status_code=400, detail=validation["error"])

    # Log warnings if any
    for warning in validation.get("warnings", []):
        logger.warning("[WARNING] Upload validation: %s", warning)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        size=bytes_read,
        uploaded_at=datetime.now(UTC).isoformat(),
    )
