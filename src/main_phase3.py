"""
Phase 3 - Step 1: Load a manageable patch from the raw TMC-2 image
without pulling the full ~1.18 GB image into RAM.
"""
from config import TMC2_IMG_PATH, TMC2_SHAPE, TMC2_DTYPE
from io_utils import load_tmc2_memmap, extract_patch, print_patch_stats

# Defined AOI (Area of Interest) for this first test patch.
# rows 50000-54000, columns 1000-3000 -> a 4000 x 2000 patch
ROW_RANGE = (50000, 54000)
COL_RANGE = (1000, 3000)


def main():
    print(f"Opening memmap: {TMC2_IMG_PATH}")
    tmc2 = load_tmc2_memmap(TMC2_IMG_PATH, shape=TMC2_SHAPE, dtype=TMC2_DTYPE)
    print(f"Full memmap shape: {tmc2.shape}, dtype: {tmc2.dtype}")

    patch = extract_patch(tmc2, ROW_RANGE, COL_RANGE)
    print_patch_stats(patch, label="TMC-2 test patch (rows 50000:54000, cols 1000:3000)")


if __name__ == "__main__":
    main()