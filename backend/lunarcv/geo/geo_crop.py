"""
geo_crop.py — Data-driven geographic cropping for LunarCV.

Uses the OHRC per-pixel geometry CSV and LRO footprint coordinates to
compute the exact overlapping region between the two sensors, replacing
hardcoded pixel ranges with geometry-derived crops.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GeoFootprint:
    """Geographic footprint of an image or sub-region."""

    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

    @property
    def lat_range(self) -> float:
        return self.max_lat - self.min_lat

    @property
    def lon_range(self) -> float:
        return self.max_lon - self.min_lon

    def intersection(self, other: GeoFootprint) -> GeoFootprint | None:
        """Compute intersection with another footprint. Returns None if no overlap."""
        min_lat = max(self.min_lat, other.min_lat)
        max_lat = min(self.max_lat, other.max_lat)
        min_lon = max(self.min_lon, other.min_lon)
        max_lon = min(self.max_lon, other.max_lon)
        if min_lat < max_lat and min_lon < max_lon:
            return GeoFootprint(min_lat, max_lat, min_lon, max_lon)
        return None


def parse_ohrc_geometry_csv(csv_path: Path) -> dict:
    """
    Parse the OHRC per-pixel geometry CSV to build a scan-to-latlon mapping.

    The CSV has columns: Longitude, Latitude, Pixel, Scan
    Where Scan = row (along-track), Pixel = column (cross-track).

    Returns a dict with:
        scan_to_lat: dict mapping scan_line -> (min_lat, max_lat)
        scan_to_lon: dict mapping scan_line -> (min_lon, max_lon)
        full_footprint: GeoFootprint for the entire image
        n_scans: int, total number of unique scan lines
        n_pixels_per_scan: int, max pixel index + 1
    """
    scan_lats: dict[int, list[float]] = {}
    scan_lons: dict[int, list[float]] = {}
    all_lats = []
    all_lons = []
    max_pixel = 0

    with open(csv_path) as f:
        reader = csv.reader(f)
        header = next(reader)
        logger.info(f"OHRC geometry CSV columns: {header}")

        for row in reader:
            lon, lat = float(row[0]), float(row[1])
            pixel, scan = int(row[2]), int(row[3])

            all_lats.append(lat)
            all_lons.append(lon)
            max_pixel = max(max_pixel, pixel)

            if scan not in scan_lats:
                scan_lats[scan] = []
                scan_lons[scan] = []
            scan_lats[scan].append(lat)
            scan_lons[scan].append(lon)

    # Build scan-to-range mappings
    scan_to_lat = {s: (min(vs), max(vs)) for s, vs in scan_lats.items()}
    scan_to_lon = {s: (min(vs), max(vs)) for s, vs in scan_lons.items()}

    full_footprint = GeoFootprint(
        min_lat=min(all_lats),
        max_lat=max(all_lats),
        min_lon=min(all_lons),
        max_lon=max(all_lons),
    )

    return {
        "scan_to_lat": scan_to_lat,
        "scan_to_lon": scan_to_lon,
        "full_footprint": full_footprint,
        "n_scans": len(scan_lats),
        "n_pixels_per_scan": max_pixel + 1,
    }


def ohrc_patch_footprint(
    geom: dict,
    row_range: tuple[int, int],
    col_range: tuple[int, int],
    image_shape: tuple[int, int] = (90148, 12000),
) -> GeoFootprint:
    """
    Compute the geographic footprint of an OHRC sub-patch.

    Uses the geometry CSV scan-to-latlon mapping for precise latitude,
    and linear interpolation on pixel columns for longitude.

    Parameters
    ----------
    geom : dict from parse_ohrc_geometry_csv()
    row_range : (row_start, row_end) in OHRC pixel coordinates
    col_range : (col_start, col_end) in OHRC pixel coordinates
    image_shape : (total_rows, total_cols)
    """
    r0, r1 = row_range
    c0, c1 = col_range
    total_rows, total_cols = image_shape

    scan_to_lat = geom["scan_to_lat"]
    scan_to_lon = geom["scan_to_lon"]
    full_fp = geom["full_footprint"]

    # Find latitude range: use nearest available scan lines
    sorted_scans = sorted(scan_to_lat.keys())

    def lat_at_scan(target_scan: int) -> tuple[float, float]:
        """Interpolate lat range at a target scan line."""
        if target_scan in scan_to_lat:
            return scan_to_lat[target_scan]
        # Find bracketing scans
        below = [s for s in sorted_scans if s <= target_scan]
        above = [s for s in sorted_scans if s >= target_scan]
        if not below:
            return scan_to_lat[sorted_scans[0]]
        if not above:
            return scan_to_lat[sorted_scans[-1]]
        s_lo, s_hi = below[-1], above[0]
        if s_lo == s_hi:
            return scan_to_lat[s_lo]
        t = (target_scan - s_lo) / (s_hi - s_lo)
        lat_lo = scan_to_lat[s_lo]
        lat_hi = scan_to_lat[s_hi]
        return (
            lat_lo[0] + t * (lat_hi[0] - lat_lo[0]),
            lat_lo[1] + t * (lat_hi[1] - lat_lo[1]),
        )

    lat_at_r0 = lat_at_scan(r0)
    lat_at_r1 = lat_at_scan(r1)

    # Scan 0 is the top (northernmost) → higher lat values
    # Scan 90147 is the bottom (southernmost) → lower lat values
    all_lats = [lat_at_r0[0], lat_at_r0[1], lat_at_r1[0], lat_at_r1[1]]
    min_lat = min(all_lats)
    max_lat = max(all_lats)

    # For longitude: linear interpolation based on column fraction
    # The full image spans full_fp.min_lon to full_fp.max_lon across total_cols columns
    lon_per_pixel = full_fp.lon_range / total_cols
    min_lon = full_fp.min_lon + c0 * lon_per_pixel
    max_lon = full_fp.min_lon + c1 * lon_per_pixel

    return GeoFootprint(min_lat, max_lat, min_lon, max_lon)


def geo_to_lro_pixels(
    footprint: GeoFootprint,
    lro_footprint: GeoFootprint,
    lro_shape: tuple[int, int],
    margin_frac: float = 0.05,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Convert a geographic footprint to LRO NAC pixel coordinates.

    Assumes a linear (equirectangular) mapping from lat/lon to pixel coordinates.
    North-up convention: row 0 = max_lat (north), row N = min_lat (south).

    Parameters
    ----------
    footprint : GeoFootprint of the target region
    lro_footprint : GeoFootprint of the full LRO NAC image
    lro_shape : (rows, cols) of the LRO NAC image
    margin_frac : fractional margin to add around the crop (default 5%)

    Returns
    -------
    (row_start, row_end), (col_start, col_end) — pixel coordinates in LRO NAC
    """
    lro_h, lro_w = lro_shape
    lro_lat_range = lro_footprint.lat_range
    lro_lon_range = lro_footprint.lon_range

    # Latitude → row (north-up: row 0 = max_lat)
    lat_per_row = lro_lat_range / lro_h
    row_top = (lro_footprint.max_lat - footprint.max_lat) / lat_per_row
    row_bot = (lro_footprint.max_lat - footprint.min_lat) / lat_per_row

    # Longitude → col
    lon_per_col = lro_lon_range / lro_w
    col_left = (footprint.min_lon - lro_footprint.min_lon) / lon_per_col
    col_right = (footprint.max_lon - lro_footprint.min_lon) / lon_per_col

    # Add margin
    row_margin = (row_bot - row_top) * margin_frac
    col_margin = (col_right - col_left) * margin_frac

    r0 = max(0, int(row_top - row_margin))
    r1 = min(lro_h, int(row_bot + row_margin))
    c0 = max(0, int(col_left - col_margin))
    c1 = min(lro_w, int(col_right + col_margin))

    return (r0, r1), (c0, c1)


def compute_isotropic_scale(src_gsd: float, ref_gsd: float) -> float:
    """
    Compute the isotropic scale ratio between source and reference.

    Returns the factor by which the source image must be downscaled
    to match the reference resolution.

    For OHRC (0.26 m/px) vs LRO NAC (1.60 m/px):
      scale = 1.60 / 0.26 ≈ 6.15
      → OHRC must be downscaled by 6.15x in both dimensions.
    """
    return ref_gsd / src_gsd
