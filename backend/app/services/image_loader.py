"""Universal image loader with auto-detection for lunar .IMG formats."""

from pathlib import Path

import cv2
import numpy as np

from lunarcv.io.raster import (
    extract_patch,
    load_lro_nac_memmap,
    load_ohrc_memmap,
    load_pds_memmap,
    load_tmc2_memmap,
)


class ImageLoadError(Exception):
    """Raised when image cannot be loaded."""

    pass


def detect_img_format(file_path: Path) -> str:
    """
    Detect lunar .IMG format type.

    Returns: 'lro_nac', 'ohrc', 'tmc2', 'generic', or 'unknown'
    """
    format_type = "generic"
    # Try parsing as a PDS3 label, then a PDS4 XML sidecar.
    try:
        arr, _ = load_pds_memmap(file_path)
        del arr
        return "pds"
    except Exception:
        format_type = "generic"

    # Check file size for known formats
    file_size = file_path.stat().st_size

    # OHRC: 90148 rows × 12000 cols × 1 byte = 1,081,776,000 bytes
    if abs(file_size - 1_081_776_000) < 1000:
        return "ohrc"

    # TMC-2: 148108 rows × 4000 cols × 2 bytes = 1,184,864,000 bytes
    if abs(file_size - 1_184_864_000) < 1000:
        return "tmc2"

    # Try generic cv2.imread()
    return format_type


def load_lunar_img(
    file_path: Path, format_type: str, max_dimension: int = 8192
) -> np.ndarray:
    """
    Load lunar .IMG file using appropriate memory-mapped loader.

    Handles: lro_nac, ohrc, tmc2
    Extracts center patch if image exceeds max_dimension.
    """
    if format_type == "pds":
        arr, meta = load_pds_memmap(file_path)
    elif format_type == "lro_nac":
        arr, meta = load_lro_nac_memmap(file_path)
    elif format_type == "ohrc":
        arr = load_ohrc_memmap(file_path)
    elif format_type == "tmc2":
        arr = load_tmc2_memmap(file_path)
    else:
        raise ImageLoadError(f"Unsupported lunar format: {format_type}")

    # Extract patch if too large
    h, w = arr.shape
    if h > max_dimension or w > max_dimension:
        patch_h = min(h, max_dimension)
        patch_w = min(w, max_dimension)
        row_start = max(0, (h - patch_h) // 2)
        col_start = max(0, (w - patch_w) // 2)
        arr = extract_patch(
            arr,
            (row_start, row_start + patch_h),
            (col_start, col_start + patch_w),
        )

    return arr


def normalize_to_uint8(
    arr: np.ndarray, p_low: float = 1.0, p_high: float = 99.0
) -> np.ndarray:
    """
    Normalize any bit depth to uint8 using percentile stretch.

    Handles uint8, uint16, float32, float64.
    """
    if arr.dtype == np.uint8:
        return arr

    # Compute percentiles
    v_min, v_max = np.percentile(arr, (p_low, p_high))
    if v_max <= v_min:
        v_max = v_min + 1.0

    # Stretch and clip
    stretched = np.clip(
        (arr.astype(np.float32) - v_min) / (v_max - v_min) * 255.0, 0, 255
    )
    return stretched.astype(np.uint8)


def load_image_auto(
    file_path: Path, max_dimension: int = 8192
) -> tuple[np.ndarray, dict]:
    """
    Auto-detect format and load image with fallback chain.

    Returns: (uint8 grayscale array, metadata dict)
    Metadata: {format, original_shape, dtype, patch_extracted}
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    # Try lunar .IMG formats
    if suffix in [".img"]:
        format_type = detect_img_format(file_path)

        if format_type in ["pds", "lro_nac", "ohrc", "tmc2"]:
            try:
                original_shape = (
                    load_pds_memmap(file_path)[0].shape
                    if format_type == "pds"
                    else None
                )
                arr = load_lunar_img(file_path, format_type, max_dimension)
                if original_shape is None:
                    original_shape = arr.shape
                arr_uint8 = normalize_to_uint8(arr)

                return arr_uint8, {
                    "format": format_type,
                    "original_shape": original_shape,
                    "dtype": str(arr.dtype),
                    "patch_extracted": (
                        arr.shape[0] < original_shape[0]
                        or arr.shape[1] < original_shape[1]
                    ),
                }
            except Exception as e:
                raise ImageLoadError(
                    f"PDS .IMG parsing failed for {file_path.name}: {e}"
                ) from e

    # Standard formats or fallback
    try:
        arr = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
        if arr is None:
            raise ImageLoadError(
                f"Cannot load {file_path.name}. "
                f"Tried lunar .IMG loaders and cv2.imread() - all failed."
            )

        original_shape = arr.shape
        arr_uint8 = normalize_to_uint8(arr)

        return arr_uint8, {
            "format": "standard",
            "original_shape": original_shape,
            "dtype": str(arr.dtype),
            "patch_extracted": False,
        }
    except Exception as e:
        raise ImageLoadError(f"Failed to load {file_path.name}: {e}") from e
