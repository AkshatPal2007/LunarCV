"""Registration algorithms: outlier rejection, transforms, sub-pixel refinement."""

from lunarcv.registration.outlier_rejection import magsac_filter, print_match_stats
from lunarcv.registration.transform import compute_registration, make_overlay, make_checkerboard
from lunarcv.registration.subpixel import refine_matches
from lunarcv.registration.spatial_uniformity import spatial_uniformity_report

__all__ = [
    "magsac_filter",
    "print_match_stats",
    "compute_registration",
    "make_overlay",
    "make_checkerboard",
    "refine_matches",
    "spatial_uniformity_report",
]
