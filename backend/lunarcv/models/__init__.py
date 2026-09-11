"""
Data models and pipeline management for lunar image registration.

Usage:
    from lunarcv.models import LunarImage, MatchSet, Pipeline

    pipeline = Pipeline("ohrc_to_nac_demo")
    source = LunarImage.load(pipeline.get_stage_output("normalize_source"))
"""

from .objects import (
    EvaluationMetrics,
    LunarImage,
    MatchSet,
    RegistrationResult,
    TransformModel,
)
from .pipeline import Pipeline

__all__ = [
    "EvaluationMetrics",
    "LunarImage",
    "MatchSet",
    "Pipeline",
    "RegistrationResult",
    "TransformModel",
]
