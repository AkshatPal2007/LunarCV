"""
Registration-related Pydantic schemas.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from .common import JobStatus


class RegistrationJobCreate(BaseModel):
    """Request to create a registration job."""
    source_image_id: str = Field(..., description="Uploaded source image ID")
    reference_image_id: str = Field(..., description="Uploaded reference image ID")
    matcher: str = Field(default="lightglue", description="Matcher to use (lightglue, loftr, rift2)")


class RegistrationJobResponse(BaseModel):
    """Response after creating a registration job."""
    job_id: str
    status: JobStatus
    created_at: str


class RegistrationJobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: JobStatus
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class RegistrationResults(BaseModel):
    """Registration results."""
    job_id: str
    status: JobStatus
    metrics: Optional[Dict[str, Any]] = None
    registered_image_url: Optional[str] = None
    overlay_image_url: Optional[str] = None
    checkerboard_image_url: Optional[str] = None
    correspondence_csv_url: Optional[str] = None
    error: Optional[str] = None


class UploadResponse(BaseModel):
    """Response after uploading an image."""
    file_id: str
    filename: str
    size: int
    uploaded_at: str
