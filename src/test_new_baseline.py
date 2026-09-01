"""
test_new_baseline.py — Test updated config and io_utils on new OHRC <-> LRO NAC RE baseline.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    OHRC_IMG_PATH,
    OHRC_SHAPE,
    OHRC_DTYPE,
    OHRC_GSD,
    LRO_IMG_PATH,
    LRO_GSD,
    SCALE_RATIO_LRO_TO_OHRC,
)
from io_utils import load_ohrc_memmap, load_lro_nac_memmap, extract_patch, print_patch_stats

def main():
    print("=" * 65)
    print("TESTING REFACTORED BASELINE WITH IO_UTILS & CONFIG")
    print("=" * 65)

    # 1. Load OHRC
    print(f"\n[1/3] Loading OHRC from config:")
    print(f"  Path: {OHRC_IMG_PATH}")
    ohrc_mm = load_ohrc_memmap(OHRC_IMG_PATH, shape=OHRC_SHAPE, dtype=OHRC_DTYPE)
    patch_ohrc = extract_patch(ohrc_mm, (10000, 12000), (4000, 6000))
    print_patch_stats(patch_ohrc, label="OHRC Patch (2000x2000)")

    # 2. Load LRO NAC RE
    print(f"\n[2/3] Loading LRO NAC RE from config:")
    print(f"  Path: {LRO_IMG_PATH}")
    lro_mm, meta = load_lro_nac_memmap(LRO_IMG_PATH)
    print(f"  LRO PDS parsed header: lines={meta['lines']}, samples={meta['line_samples']}, offset={meta['offset']} bytes")
    patch_lro = extract_patch(lro_mm, (5000, 7000), (500, 1500))
    print_patch_stats(patch_lro, label="LRO NAC Patch (2000x1000)")

    # 3. Scale ratio verification
    print(f"\n[3/3] Scale Relationship:")
    print(f"  OHRC GSD : {OHRC_GSD} m/px")
    print(f"  LRO GSD  : {LRO_GSD} m/px")
    print(f"  Ratio    : {SCALE_RATIO_LRO_TO_OHRC:.2f}x (1 LRO px = {SCALE_RATIO_LRO_TO_OHRC:.2f} OHRC px)")

    print("\n" + "=" * 65)
    print("SUCCESS: Config & IO Utils verified with new baseline pair.")
    print("=" * 65)

if __name__ == "__main__":
    main()
