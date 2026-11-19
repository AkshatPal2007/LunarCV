"""Contracts for the real-data registration workspace."""

from typing import Any

from pydantic import BaseModel, Field

from .registration import RegistrationJobCreate


class PairAvailability(BaseModel):
    pair_id: str
    name: str
    dataset_split: str
    source_product_id: str
    reference_product_id: str
    source_sensor: str
    reference_sensor: str
    available: bool
    unavailable_reason: str | None
    prior_description: str
    ground_truth_status: str
    registration_request: RegistrationJobCreate


class ProductMetadata(BaseModel):
    file_id: str
    filename: str
    shape: tuple[int, int]
    dtype: str
    georeferenced: bool
    bands: int
    format: str


class JobSummary(BaseModel):
    job_id: str
    status: str
    progress: int | None = None
    message: str | None = None
    created_at: str | None = None
    completed_at: str | None = None
    quality_decision: str | None = None
    source_name: str
    reference_name: str


class CorrespondencePoint(BaseModel):
    point_id: int
    source: tuple[float, float]
    reference: tuple[float, float]
    confidence: float = Field(allow_inf_nan=False)
    secondary_agreement: bool
    refined: bool
    fit_residual_reference_px: float = Field(ge=0, allow_inf_nan=False)


class VisualizationResponse(BaseModel):
    job_id: str
    mapping: dict[str, Any] | None
    points: list[CorrespondencePoint]
    artifacts: dict[str, str]
