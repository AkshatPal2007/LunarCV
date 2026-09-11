"""Registration algorithms: outlier rejection, transforms, sub-pixel refinement."""

from lunarcv.registration.outlier_rejection import magsac_filter, print_match_stats
from lunarcv.registration.spatial_uniformity import spatial_uniformity_report
from lunarcv.registration.subpixel import refine_matches
from lunarcv.registration.transform import (
    compute_registration,
    estimate_transform,
    make_checkerboard,
    make_overlay,
    make_professional_suite,
    warp_images,
)

__all__ = [
    "magsac_filter",
    "print_match_stats",
    "compute_registration",
    "estimate_transform",
    "warp_images",
    "make_overlay",
    "make_checkerboard",
    "make_professional_suite",
    "refine_matches",
    "spatial_uniformity_report",
]
