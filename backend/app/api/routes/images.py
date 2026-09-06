"""Image listing endpoints."""

from fastapi import APIRouter

from app.config import settings
from app.schemas.images import ImageInfo

router = APIRouter()


@router.get("/images", response_model=list[ImageInfo])
async def list_images():
    """
    List all available images from data/raw/ and data/uploads/.

    Returns list of images with file_id, filename, source, and size.
    """
    images = []

    # Scan data/raw/ for demo images
    if settings.RAW_DIR.exists():
        for file in settings.RAW_DIR.glob("*"):
            if file.is_file() and file.suffix.lower() in [
                ".img",
                ".tif",
                ".tiff",
                ".png",
                ".jpg",
                ".jpeg",
            ]:
                images.append(
                    ImageInfo(
                        file_id=file.stem,
                        filename=file.name,
                        source="raw",
                        size=file.stat().st_size,
                    )
                )

    # Scan data/uploads/ for user-uploaded images
    if settings.UPLOAD_DIR.exists():
        for file in settings.UPLOAD_DIR.glob("*"):
            if file.is_file() and file.suffix.lower() in [
                ".img",
                ".tif",
                ".tiff",
                ".png",
                ".jpg",
                ".jpeg",
            ]:
                images.append(
                    ImageInfo(
                        file_id=file.stem,
                        filename=file.name,
                        source="uploads",
                        size=file.stat().st_size,
                    )
                )

    return images
