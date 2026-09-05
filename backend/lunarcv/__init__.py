"""
LunarCV - Multi-modal lunar image registration library.

Core modules:
- io: Memory-mapped image loading
- matching: Feature matchers (LightGlue, LoFTR, RIFT2)
- registration: Outlier rejection, transforms, sub-pixel refinement
- preprocessing: Image normalization
"""

__version__ = "0.1.0"

# Re-export commonly used classes and functions
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.registration.outlier_rejection import magsac_filter
from lunarcv.registration.transform import compute_registration
from lunarcv.io.raster import (
    load_ohrc_memmap,
    load_lro_nac_memmap,
    extract_patch,
)

__all__ = [
    "LightGlueFeatureMatcher",
    "magsac_filter",
    "compute_registration",
    "load_ohrc_memmap",
    "load_lro_nac_memmap",
    "extract_patch",
]
