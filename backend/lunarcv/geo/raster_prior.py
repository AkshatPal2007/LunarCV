"""Geographic prior only when both rasters declare the same projected CRS.

Raw EDR images without camera/geolocation metadata are explicitly unsupported
here. A footprint bounding box is never substituted for a raw camera model.
"""

import warnings
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning
from rasterio.windows import from_bounds


def overlap_windows(source_path, reference_path):
    if any(Path(p).suffix.lower() == ".img" for p in (source_path, reference_path)):
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with (
            rasterio.open(source_path) as source,
            rasterio.open(reference_path) as reference,
        ):
            if (
                source.crs is None
                or source.crs != reference.crs
                or not source.crs.is_projected
            ):
                return None
            if any(
                abs(ds.transform.b) > 1e-10 or abs(ds.transform.d) > 1e-10
                for ds in (source, reference)
            ):
                return None  # Rotated/geographic rasters need an explicit adapter.
            left = max(source.bounds.left, reference.bounds.left)
            bottom = max(source.bounds.bottom, reference.bounds.bottom)
            right = min(source.bounds.right, reference.bounds.right)
            top = min(source.bounds.top, reference.bounds.top)
            if left >= right or bottom >= top:
                raise ValueError("Georeferenced images have no geographic overlap")

            def bounds(dataset):
                window = from_bounds(left, bottom, right, top, dataset.transform)
                return (
                    max(0, int(np.floor(window.col_off))),
                    max(0, int(np.floor(window.row_off))),
                    min(dataset.width, int(np.ceil(window.col_off + window.width))),
                    min(dataset.height, int(np.ceil(window.row_off + window.height))),
                )

            return {
                "source_bounds": bounds(source),
                "reference_bounds": bounds(reference),
                "source_scale_xy": (
                    abs(reference.transform.a / source.transform.a),
                    abs(reference.transform.e / source.transform.e),
                ),
                "description": "Intersection and GSD from matching projected raster CRS; geographic metadata is a search prior, not independent truth",
            }
