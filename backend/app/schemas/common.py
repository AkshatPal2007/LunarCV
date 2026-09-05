"""
Common Pydantic schemas.
"""

from enum import Enum
from pydantic import BaseModel


class JobStatus(str, Enum):
    """Registration job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
