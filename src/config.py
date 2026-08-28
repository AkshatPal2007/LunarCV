"""
Paths and values for the project.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Main data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# TMC-2 product directory
TMC2_DIR = (
    RAW_DIR
    / "tmc2"
    / "ch2_tmc_ncn_20260813T0627378557_d_img_d18"
)

# Actual calibrated image
TMC2_IMG_PATH = (
    TMC2_DIR
    / "data"
    / "calibrated"
    / "20260813"
    / "ch2_tmc_ncn_20260813T0627378557_d_img_d18.img"
)

# Output directories
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"

# Processed data: per-sensor subdirectories
TMC2_PROCESSED_DIR = PROCESSED_DIR / "tmc2"

# Image properties from metadata
TMC2_SHAPE = (148108, 4000)
TMC2_DTYPE = "uint16"

# Create required output directories on import
TMC2_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)