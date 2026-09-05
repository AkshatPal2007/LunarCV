"""
Image upload endpoints.
"""

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.schemas.registration import UploadResponse

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

    # Save file
    content = await file.read()

    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    with open(save_path, "wb") as f:
        f.write(content)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        size=len(content),
        uploaded_at=datetime.utcnow().isoformat(),
    )
