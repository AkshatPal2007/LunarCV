"""Image listing schemas."""

from pydantic import BaseModel


class ImageInfo(BaseModel):
    """Information about an available image."""

    file_id: str
    filename: str
    source: str  # 'raw' or 'uploads'
    size: int
