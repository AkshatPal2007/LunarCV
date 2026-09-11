"""
Common Pydantic schemas.
"""

from enum import StrEnum

from pydantic import BaseModel


class JobStatus(StrEnum):
    """Registration job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
