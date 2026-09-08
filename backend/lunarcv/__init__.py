"""
LunarCV — Multi-modal lunar image registration library.

Core packages:
  geo          : Metadata, BoundingBox, geographic prior & tiling
  matching     : Matcher ABC, LightGlue, RIFT2 (optional), EnsembleMatcher
  registration : MAGSAC++, spatial uniformity, sub-pixel, transform/warp
  evaluation   : RMSE, spatial uniformity score, quality gate
  io           : Memory-mapped image loading (OHRC, LRO NAC)
  preprocessing: Image normalisation utilities
"""

__version__ = "0.2.0"

# Core I/O
from lunarcv.io.raster import load_ohrc_memmap, load_lro_nac_memmap, extract_patch

# Matching
from lunarcv.matching.matcher import Matcher
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.matching.ensemble import EnsembleMatcher

# Registration
from lunarcv.registration.outlier_rejection import magsac_filter
from lunarcv.registration.transform import compute_registration

# Evaluation
from lunarcv.evaluation.metrics import (
    RegistrationMetrics,
    calculate_rmse,
    evaluate_spatial_uniformity,
    quality_gate,
)

# Geo
from lunarcv.geo.metadata import BoundingBox, ImageMetadata
from lunarcv.geo.geo_prior import compute_overlap, estimate_scale_ratio, generate_tiles

__all__ = [
    # I/O
    "load_ohrc_memmap", "load_lro_nac_memmap", "extract_patch",
    # Matching
    "Matcher", "LightGlueFeatureMatcher", "EnsembleMatcher",
    # Registration
    "magsac_filter", "compute_registration",
    # Evaluation
    "RegistrationMetrics", "calculate_rmse", "evaluate_spatial_uniformity", "quality_gate",
    # Geo
    "BoundingBox", "ImageMetadata", "compute_overlap", "estimate_scale_ratio", "generate_tiles",
]
