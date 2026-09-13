"""
config.py — Central configuration for LunarCV.

Defines dataset paths, sensor geometries, output directories, and default parameters.
Updated for the benchmark baseline: Chandrayaan-2 OHRC <-> NASA LRO NAC (M1350459544RE).
"""

from pathlib import Path

# backend/lunarcv/config.py -> backend/lunarcv/ -> backend/ -> PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Main data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"

# Output directories
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
EVAL_DIR = OUTPUT_DIR / "evaluations"
SUBMISSION_DIR = OUTPUT_DIR / "submission"
PIPELINE_OUTPUT_DIR = OUTPUT_DIR / "pipeline"  # For Pipeline object tracking

# ---------------------------------------------------------------------------
# Chandrayaan-2 OHRC Baseline Product
# ---------------------------------------------------------------------------
OHRC_BASE_DIR = RAW_DIR / "tmc2" / "baseline"
OHRC_IMG_PATH = (
    OHRC_BASE_DIR
    / "data"
    / "calibrated"
    / "20210401"
    / "ch2_ohr_ncp_20210401T2357376656_d_img_d18.img"
)
OHRC_XML_PATH = (
    OHRC_BASE_DIR
    / "data"
    / "calibrated"
    / "20210401"
    / "ch2_ohr_ncp_20210401T2357376656_d_img_d18.xml"
)
OHRC_GEOM_CSV = (
    OHRC_BASE_DIR
    / "geometry"
    / "calibrated"
    / "20210401"
    / "ch2_ohr_ncp_20210401T2357376656_g_grd_d18.csv"
)

OHRC_SHAPE = (90148, 12000)
OHRC_DTYPE = "uint8"
OHRC_OFFSET = 0  # Raw binary starts at offset 0
OHRC_GSD = 0.26  # meters / pixel
OHRC_LAT_RANGE = (-13.889, -13.055)
OHRC_LON_RANGE = (25.128, 25.246)

# ---------------------------------------------------------------------------
# NASA LRO NAC Baseline Product (Right Camera, Summed mode)
# ---------------------------------------------------------------------------
LRO_DIR = RAW_DIR / "lro"
LRO_IMG_PATH = LRO_DIR / "M1350459544RE.IMG"

LRO_SHAPE = (52224, 2532)
LRO_DTYPE = "uint8"
LRO_OFFSET = 2532  # 1 PDS record (RECORD_BYTES = 2532)
LRO_GSD = 1.60  # meters / pixel (1.55m cross-track, 1.66m along-track)
LRO_LAT_RANGE = (-15.88, -13.00)
LRO_LON_RANGE = (25.08, 25.41)

# Physical GSD scale factors:
# OHRC GSD: 0.26 m/px
# LRO NAC Summed GSD: 1.55 m/px cross-track, 1.66 m/px along-track
SCALE_X_LRO_TO_OHRC = 1.55 / 0.26  # ~5.9615
SCALE_Y_LRO_TO_OHRC = 1.66 / 0.26  # ~6.3846
SCALE_LRO_TO_OHRC = (SCALE_X_LRO_TO_OHRC + SCALE_Y_LRO_TO_OHRC) / 2.0  # ~6.173x

# Calibrated geographic overlap bounding boxes for the baseline pair:
# Anchored on the iconic high-relief Landmark Impact Crater (Lat -13.84°, Lon +25.18°):
OHRC_OVERLAP_PATCH_ROWS = (82500, 88500)
OHRC_OVERLAP_PATCH_COLS = (800, 5800)
LRO_OVERLAP_PATCH_ROWS = (13300, 14600)
LRO_OVERLAP_PATCH_COLS = (1050, 1950)
# Processed data subdirectories
OHRC_PROCESSED_DIR = PROCESSED_DIR / "ohrc"
LRO_PROCESSED_DIR = PROCESSED_DIR / "lro"
MATCHES_PROCESSED_DIR = PROCESSED_DIR / "matches"

# Create required output directories on import
OHRC_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LRO_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MATCHES_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)
SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
