"""
geo_prior.py — Geographic prior estimation and tiling.
Handles overlapping region calculation, scale ratio estimation,
and automatic tiling for large bounding boxes.
"""

from __future__ import annotations

from dataclasses import dataclass

from lunarcv.geo.metadata import BoundingBox, ImageMetadata


@dataclass
class Tile:
    """Represents a localised crop inside an image."""

    x: int
    y: int
    width: int
    height: int
    bbox: BoundingBox | None = None


def compute_overlap(
    src_meta: ImageMetadata, ref_meta: ImageMetadata
) -> BoundingBox | None:
    """
    Compute the geographic intersection of source and reference images.
    Returns None if they do not overlap or if either has no bbox.
    """
    if not src_meta.bbox or not ref_meta.bbox:
        return None
    return src_meta.bbox.intersection(ref_meta.bbox)


def estimate_scale_ratio(src_meta: ImageMetadata, ref_meta: ImageMetadata) -> float:
    """
    Estimate the GSD-based scale ratio between source and reference.

    Returns scale = ref_gsd / src_gsd.
    > 1.0  →  source is higher resolution (needs downscaling to match ref).
    < 1.0  →  source is lower resolution.
    """
    if src_meta.gsd_meters <= 0 or ref_meta.gsd_meters <= 0:
        raise ValueError("GSD must be strictly positive.")
    return ref_meta.gsd_meters / src_meta.gsd_meters


def generate_tiles(
    image_width: int,
    image_height: int,
    tile_size: int,
    overlap: int = 0,
) -> list[Tile]:
    """
    Divide an image into a grid of (possibly overlapping) tiles.
    Tiny sliver tiles at the trailing edges are discarded.
    """
    tiles: list[Tile] = []
    stride = tile_size - overlap
    if stride <= 0:
        raise ValueError("overlap must be strictly less than tile_size.")

    for y in range(0, image_height, stride):
        for x in range(0, image_width, stride):
            w = min(tile_size, image_width - x)
            h = min(tile_size, image_height - y)
            # Discard trailing slivers
            if w < tile_size // 4 and x > 0:
                continue
            if h < tile_size // 4 and y > 0:
                continue
            tiles.append(Tile(x=x, y=y, width=w, height=h))

    return tiles


def geo_bbox_to_pixel_coords(
    bbox: BoundingBox, img_meta: ImageMetadata
) -> tuple[int, int, int, int]:
    """
    Convert a geographic bounding box to pixel coordinates (x, y, w, h)
    within an image. Assumes a simple linear (equirectangular) projection —
    accurate for small patches.
    """
    if not img_meta.bbox:
        raise ValueError("ImageMetadata must have a valid bbox.")

    img_bbox = img_meta.bbox
    lon_range = img_bbox.max_lon - img_bbox.min_lon
    lat_range = img_bbox.max_lat - img_bbox.min_lat

    if lon_range <= 0 or lat_range <= 0:
        return (0, 0, img_meta.width, img_meta.height)

    # Longitude → X (left to right)
    min_x_frac = (bbox.min_lon - img_bbox.min_lon) / lon_range
    max_x_frac = (bbox.max_lon - img_bbox.min_lon) / lon_range

    # Latitude → Y  (top = max_lat, bottom = min_lat, North-up)
    min_y_frac = (img_bbox.max_lat - bbox.max_lat) / lat_range
    max_y_frac = (img_bbox.max_lat - bbox.min_lat) / lat_range

    x1 = max(0, int(min_x_frac * img_meta.width))
    x2 = min(img_meta.width, int(max_x_frac * img_meta.width))
    y1 = max(0, int(min_y_frac * img_meta.height))
    y2 = min(img_meta.height, int(max_y_frac * img_meta.height))

    return (x1, y1, x2 - x1, y2 - y1)
