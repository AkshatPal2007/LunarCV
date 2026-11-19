"""Compatibility adapters for the shared bounded product reader.

No format guessing from file size and no implicit center crop. Registration uses
RegistrationEngine directly; these helpers retain explicit crop/native metadata
for callers of the older loader API.
"""

from pathlib import Path

import numpy as np

from lunarcv.io.products import describe_product, normalize_product, read_product


class ImageLoadError(Exception):
    """Raised when declared imagery cannot be loaded safely."""


def detect_img_format(file_path: Path) -> str:
    try:
        return "pds" if describe_product(file_path)["format"] == "PDS" else "standard"
    except (OSError, ValueError) as exc:
        raise ImageLoadError(str(exc)) from exc


def _bounded_product(file_path, max_dimension, bounds):
    try:
        metadata = describe_product(file_path)
        x0, y0, x1, y1 = bounds or (0, 0, metadata["shape"][1], metadata["shape"][0])
        if max(x1 - x0, y1 - y0) > max_dimension:
            raise ValueError("Image exceeds processing limit; supply an explicit crop")
        return read_product(
            file_path, bounds=bounds, max_pixels=min(32_000_000, max_dimension**2)
        )
    except (OSError, ValueError) as exc:
        raise ImageLoadError(str(exc)) from exc


def load_lunar_img(
    file_path: Path, format_type: str, max_dimension: int = 8192, *, bounds=None
) -> np.ndarray:
    """Read a declared PDS window; format_type is a legacy compatibility argument."""
    return _bounded_product(file_path, max_dimension, bounds).data


def normalize_to_uint8(
    arr: np.ndarray, p_low: float = 1.0, p_high: float = 99.0
) -> np.ndarray:
    """Legacy array normalization, never an evaluation image generator."""
    values = arr[np.isfinite(arr)]
    if not values.size:
        raise ImageLoadError("Image contains no finite values")
    low, high = np.percentile(values, [p_low, p_high])
    if high <= low:
        raise ImageLoadError("Image has insufficient radiometric variation")
    return np.clip((arr.astype(np.float32) - low) * 255 / (high - low), 0, 255).astype(
        np.uint8
    )


def load_image_auto(
    file_path: Path, max_dimension: int = 8192, *, bounds=None
) -> tuple[np.ndarray, dict]:
    """Shared real-file loading with original dimensions and explicit window origin."""
    product = _bounded_product(file_path, max_dimension, bounds)
    return normalize_product(product), {
        "format": detect_img_format(file_path),
        "original_shape": product.original_shape,
        "dtype": str(product.data.dtype),
        "patch_extracted": product.data.shape != product.original_shape,
        "bounds_xyxy_exclusive": product.bounds,
        "pixel_convention": "zero-based centers; x=column,y=row",
    }
