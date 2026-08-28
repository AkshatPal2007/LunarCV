import numpy as np
from pathlib import Path

def load_tmc2_memmap(img_path: Path, shape: tuple, dtype: str = "uint16") -> np.memmap:
    return np.memmap(img_path, dtype = dtype, mode="r", shape=shape)

def extract_patch(memmap_array: np.memmap, row_range:tuple, col_range:tuple) -> np.ndarray:
    r0,r1 = row_range
    c0, c1 = col_range
    patch = memmap_array[r0:r1, c0:c1].copy()
    return patch

def print_patch_stats(patch: np.ndarray, label: str = "patch") ->None:
    print(f"--- {label} stats ---")
    print(f"shape : {patch.shape}")
    print(f"dtype : {patch.dtype}")
    print(f"min   : {patch.min()}")
    print(f"max   : {patch.max()}")
    print(f"mean  : {patch.mean():.4f}")
    print(f"std   : {patch.std():.4f}")