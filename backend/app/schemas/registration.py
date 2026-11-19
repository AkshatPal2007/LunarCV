"""
Registration-related Pydantic schemas.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from .common import JobStatus

PositiveFinite = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class RegistrationJobCreate(BaseModel):
    """Request to create a registration job."""

    source_image_id: str = Field(..., pattern=r"^[A-Za-z0-9_-]{1,100}$")
    reference_image_id: str = Field(..., pattern=r"^[A-Za-z0-9_-]{1,100}$")
    matcher: Literal["lightglue", "rift2", "ensemble"] = "ensemble"
    model: Literal["similarity", "affine", "homography"] = "affine"
    features: Literal["disk", "aliked", "sift"] = "aliked"
    source_bounds: tuple[int, int, int, int] | None = None
    reference_bounds: tuple[int, int, int, int] | None = None
    source_scale_xy: tuple[PositiveFinite, PositiveFinite] = (1.0, 1.0)


class RegistrationJobResponse(BaseModel):
    """Response after creating a registration job."""

    job_id: str
    status: JobStatus
    created_at: str


class RegistrationJobStatus(BaseModel):
    """Job status response."""

    job_id: str
    status: JobStatus
    progress: int | None = Field(None, description="Progress percentage (0-100)")
    message: str | None = None
    created_at: str | None
    completed_at: str | None = None


class RegistrationResults(BaseModel):
    """Registration results."""

    job_id: str
    status: JobStatus
    metrics: dict[str, Any] | None = None
    registered_image_url: str | None = None
    overlay_image_url: str | None = None
    checkerboard_image_url: str | None = None
    correspondence_csv_url: str | None = None
    transform_url: str | None = None
    science_raster_url: str | None = None
    metrics_url: str | None = None
    manifest_url: str | None = None
    error: str | None = None


class UploadResponse(BaseModel):
    """Response after uploading an image."""

    file_id: str
    filename: str
    size: int
    uploaded_at: str
