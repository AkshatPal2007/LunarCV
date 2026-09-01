"""
io_utils.py — Zero-copy memory mapping and PDS header parsing for LunarCV.

Supports:
    - Chandrayaan-2 OHRC (90148 x 12000 uint8, PDS4)
    - Chandrayaan-2 TMC-2 (148108 x 4000 uint16, PDS4)
    - NASA LRO NAC (e.g. M1350459544RE, M1529041271LE, PDS3)
"""

from __future__ import annotations

import re
from pathlib import Path
import numpy as np


def load_ohrc_memmap(
    img_path: Path,
    shape: tuple[int, int] = (90148, 12000),
    dtype: str = "uint8",
    offset: int = 0,
) -> np.memmap:
    """Open Chandrayaan-2 OHRC .img file via zero-copy np.memmap."""
    return np.memmap(img_path, dtype=dtype, mode="r", offset=offset, shape=shape)


def load_tmc2_memmap(
    img_path: Path,
    shape: tuple[int, int] = (148108, 4000),
    dtype: str = "uint16",
    offset: int = 0,
) -> np.memmap:
    """Open Chandrayaan-2 TMC-2 .img file via zero-copy np.memmap."""
    return np.memmap(img_path, dtype=dtype, mode="r", offset=offset, shape=shape)


def parse_lro_pds_header(img_path: Path) -> dict:
    """Parse key PDS3 label attributes from LRO NAC .IMG header."""
    with open(img_path, "rb") as f:
        header_text = f.read(100000).decode("latin-1", errors="ignore")

    def get_val(key: str, default=None, cast=str):
        m = re.search(rf"{key}\s*=\s*([^\r\n<]+)", header_text)
        if m:
            val_str = m.group(1).split("<")[0].strip().strip('"')
            try:
                return cast(val_str)
            except Exception:
                return val_str
        return default

    rec_bytes = get_val("RECORD_BYTES", cast=int)
    lbl_recs  = get_val("LABEL_RECORDS", cast=int)
    lines     = get_val("LINES", cast=int)
    samples   = get_val("LINE_SAMPLES", cast=int)
    bits      = get_val("SAMPLE_BITS", cast=int)

    # Offset is always LABEL_RECORDS * RECORD_BYTES in standard PDS3
    offset = (lbl_recs * rec_bytes) if (lbl_recs and rec_bytes) else 0
    dtype = np.uint8 if bits == 8 else np.uint16

    return {
        "record_bytes": rec_bytes,
        "label_records": lbl_recs,
        "lines": lines,
        "line_samples": samples,
        "sample_bits": bits,
        "offset": offset,
        "dtype": dtype,
        "shape": (lines, samples) if (lines and samples) else None,
    }


def load_lro_nac_memmap(img_path: Path) -> tuple[np.memmap, dict]:
    """Open LRO NAC .IMG file via np.memmap using header metadata."""
    meta = parse_lro_pds_header(img_path)
    if not meta["shape"]:
        raise ValueError(f"Could not parse shape from header of {img_path}")
    arr = np.memmap(img_path, dtype=meta["dtype"], mode="r", offset=meta["offset"], shape=meta["shape"])
    return arr, meta


def extract_patch(memmap_array: np.memmap, row_range: tuple[int, int], col_range: tuple[int, int]) -> np.ndarray:
    """Extract a patch from a memmapped array as an in-memory numpy array copy."""
    r0, r1 = row_range
    c0, c1 = col_range
    return memmap_array[r0:r1, c0:c1].copy()


def print_patch_stats(patch: np.ndarray, label: str = "patch") -> None:
    """Print summary statistics for an image patch."""
    print(f"--- {label} stats ---")
    print(f"shape : {patch.shape}")
    print(f"dtype : {patch.dtype}")
    print(f"min   : {patch.min()}")
    print(f"max   : {patch.max()}")
    print(f"mean  : {patch.mean():.4f}")
    print(f"std   : {patch.std():.4f}")