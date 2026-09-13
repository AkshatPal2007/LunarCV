"""
Processing pipeline configuration constants for LunarCV.

All magic numbers used in the registration pipeline are defined here
as constants for visibility and easy access by the API.
"""

# Normalization
PERCENTILE_LOW = 1.0
PERCENTILE_HIGH = 99.0

# CLAHE (Contrast Limited Adaptive Histogram Equalization)
CLAHE_ENABLED = False  # Not used by default in current pipeline
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (8, 8)

# LightGlue matcher
LIGHTGLUE_MAX_DIM = 1500
LIGHTGLUE_MAX_KEYPOINTS = 2048
LIGHTGLUE_CONF_THRESHOLD = 0.0

# Strip matching (dynamic tiling)
STRIP_HEIGHT_MIN = 256
STRIP_HEIGHT_MAX = 2048
STRIP_HEIGHT_DIVISOR = 10  # max(h_src, h_ref) / 10
STRIP_OVERLAP_MIN = 64
STRIP_OVERLAP_DIVISOR = 8  # strip_height // 8

# RIFT2 fallback
RIFT2_THRESHOLD = 5  # Invoke RIFT2 if LightGlue finds < N matches per strip

# MAGSAC++ outlier rejection
MAGSAC_REPROJ_THRESHOLD = 4.0  # pixels
MAGSAC_MAX_ITERS = 10000
MAGSAC_CONFIDENCE = 0.999
MAGSAC_MODEL = "homography"

# Spatial uniformity (grid-based distribution)
SPATIAL_GRID_ROWS = 4
SPATIAL_GRID_COLS = 4
SPATIAL_TOP_K_PER_CELL = 3

# Sub-pixel refinement
SUBPIXEL_ENABLED = True
SUBPIXEL_METHOD = "cornerSubPix"
SUBPIXEL_WIN_SIZE = (5, 5)
SUBPIXEL_MAX_ITER = 30
SUBPIXEL_EPSILON = 0.01

# Transform fitting
TRANSFORM_MODEL = "least_squares_homography"
