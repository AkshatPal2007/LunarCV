"""Validated processing settings; importing defaults does not load inference."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RegistrationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    matcher: Literal["lightglue", "rift2", "ensemble"] = "ensemble"
    features: Literal["disk", "aliked", "sift"] = "aliked"
    model: Literal["similarity", "affine", "homography"] = "affine"
    max_dim: int = Field(1536, ge=256, le=2048)
    max_keypoints: int = Field(4096, ge=128, le=8192)
    reprojection_threshold: float = Field(3.0, gt=0, le=10)
    grid_rows: int = Field(4, ge=2, le=16)
    grid_cols: int = Field(4, ge=2, le=16)
    top_k: int = Field(8, ge=1, le=32)
    tile_size: int = Field(512, ge=128, le=1024)
    tile_budget: int = Field(12, ge=0, le=32)
    max_pixels: int = Field(32_000_000, ge=4096, le=64_000_000)
    refine: bool = True
    seed: int = 20260910
    min_inliers: int = Field(12, ge=6)
    min_occupancy_pct: float = Field(50.0, ge=0, le=100)
    min_hull_pct: float = Field(20.0, ge=0, le=100)
    max_fit_rmse: float = Field(2.0, gt=0)
    max_uniformity_cv: float = Field(1.5, gt=0)
