"""Synthetic rasters test geographic window logic, never reported accuracy."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from lunarcv.geo.raster_prior import overlap_windows


def write(path, west, scale):
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=100,
        width=100,
        count=1,
        dtype="uint8",
        crs="+proj=eqc +R=1737400 +units=m +no_defs",
        transform=from_origin(west, 100, scale, scale),
    ) as dataset:
        dataset.write(np.ones((100, 100), np.uint8), 1)


def test_projected_overlap_and_gsd_are_derived_from_declared_rasters(tmp_path):
    a, b = tmp_path / "a.tif", tmp_path / "b.tif"
    write(a, 0, 1)
    write(b, 50, 2)
    prior = overlap_windows(a, b)
    assert prior["source_bounds"] == (50, 0, 100, 100)
    assert prior["reference_bounds"] == (0, 0, 25, 50)
    assert prior["source_scale_xy"] == (2.0, 2.0)


def test_projected_nonoverlap_fails_explicitly(tmp_path):
    a, b = tmp_path / "a.tif", tmp_path / "b.tif"
    write(a, 0, 1)
    write(b, 1000, 1)
    with pytest.raises(ValueError, match="no geographic overlap"):
        overlap_windows(a, b)
