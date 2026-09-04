"""
config.py — Central configuration for LunarCV.

Defines dataset paths, sensor geometries, output directories, and default parameters.
Updated for the benchmark baseline: Chandrayaan-2 OHRC <-> NASA LRO NAC (M1350459544RE).
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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
OHRC_OFFSET = 0
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

# Scale ratios between sensors (Anamorphic scaling to account for LRO 2x cross-track binning)
# Derived empirically from precise geographic overlap bounds
SCALE_Y_LRO_TO_OHRC = 15000 / 3294  # ~4.55x
SCALE_X_LRO_TO_OHRC = 6000 / 571    # ~10.5x
# Processed data subdirectories
OHRC_PROCESSED_DIR = PROCESSED_DIR / "ohrc"
LRO_PROCESSED_DIR  = PROCESSED_DIR / "lro"
MATCHES_PROCESSED_DIR = PROCESSED_DIR / "matches"

# Create required output directories on import
OHRC_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LRO_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MATCHES_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)
SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)