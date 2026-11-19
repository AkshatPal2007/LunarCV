"""Bounded real-file loading. Never silently select a center crop."""

import warnings
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning
from rasterio.windows import Window

from lunarcv.io.raster import load_pds_memmap
from lunarcv.registration.coordinates import PixelFrame


@dataclass
class ProductWindow:
    path: Path
    data: np.ndarray
    valid: np.ndarray
    original_shape: tuple[int, int]
    bounds: tuple[int, int, int, int]
    crs: object = None
    geotransform: object = None
    nodata: float | None = None

    @property
    def frame(self):
        return PixelFrame((self.bounds[0], self.bounds[1]))


def read_product(path, bounds=None, max_pixels=32_000_000):
    path = Path(path).resolve(strict=True)
    dataset = None
    if path.suffix.lower() == ".img":
        array, _ = load_pds_memmap(path)
        shape = array.shape
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", NotGeoreferencedWarning)
            dataset = rasterio.open(path)
        shape = (dataset.height, dataset.width)
    try:
        x0, y0, x1, y1 = bounds or (0, 0, shape[1], shape[0])
        if not (0 <= x0 < x1 <= shape[1] and 0 <= y0 < y1 <= shape[0]):
            raise ValueError(
                f"Crop {bounds} is outside image {shape}; bounds are x0,y0,x1,y1 exclusive"
            )
        if (x1 - x0) * (y1 - y0) > max_pixels:
            raise ValueError(
                "Processing window exceeds max_pixels; supply a metadata-derived or explicit crop"
            )
        crs, transform, nodata = None, None, None
        if dataset is None:
            data = np.array(array[y0:y1, x0:x1])
            valid = np.isfinite(data)
        else:
            window = Window(x0, y0, x1 - x0, y1 - y0)
            if dataset.count not in (1, 3, 4):
                raise ValueError(
                    "Multiband science products require an explicit verified band adapter"
                )
            bands = dataset.read(
                list(range(1, min(dataset.count, 3) + 1)), window=window
            )
            data = (
                bands[0]
                if len(bands) == 1
                else cv2.cvtColor(np.moveaxis(bands, 0, 2), cv2.COLOR_RGB2GRAY)
            )
            valid = (dataset.dataset_mask(window=window) > 0) & np.isfinite(data)
            crs = dataset.crs
            transform = dataset.window_transform(window) if crs else None
            nodata = dataset.nodata
        if not valid.any():
            raise ValueError("Image window contains no valid data")
        data = data.astype(data.dtype.newbyteorder("="), copy=False)
        return ProductWindow(
            path, data, valid, shape, (x0, y0, x1, y1), crs, transform, nodata
        )
    finally:
        if dataset:
            dataset.close()


def normalize_product(product):
    values = product.data[product.valid]
    # Deterministic sampling bounds percentile memory while preserving native dtype.
    values = values[:: max(1, len(values) // 1_000_000)]
    low, high = np.percentile(values, [1, 99])
    if not np.isfinite([low, high]).all() or high <= low:
        raise ValueError("Image window has insufficient radiometric variation")
    result = np.clip(
        (product.data.astype(np.float32) - low) * (255 / (high - low)), 0, 255
    )
    result[~product.valid] = 0
    return result.astype(np.uint8)


def describe_product(path: Path) -> dict:
    """Read declared dimensions/dtype without decoding the full image."""
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() == ".img":
        array, meta = load_pds_memmap(path)
        return {
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "georeferenced": False,
            "bands": 1,
            "format": "PDS",
        }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(path) as dataset:
            return {
                "shape": [dataset.height, dataset.width],
                "dtype": dataset.dtypes[0],
                "georeferenced": dataset.crs is not None,
                "bands": dataset.count,
                "format": dataset.driver,
            }


def validate_window(bounds, shape, max_pixels=32_000_000):
    """Validate exclusive XY bounds before allocating or queueing work."""
    x0, y0, x1, y1 = bounds or (0, 0, shape[1], shape[0])
    if not (0 <= x0 < x1 <= shape[1] and 0 <= y0 < y1 <= shape[0]):
        raise ValueError(
            "Crop must be x0,y0,x1,y1 with exclusive ends inside the original image"
        )
    if (x1 - x0) * (y1 - y0) > max_pixels:
        raise ValueError(
            "Window exceeds 32 million pixels; specify an overlap crop before registration"
        )
    return x0, y0, x1, y1
