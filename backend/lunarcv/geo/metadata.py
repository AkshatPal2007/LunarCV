"""
metadata.py — Generic metadata representation for lunar imagery.
Handles extraction of bounding boxes, GSD, and sensor information
from OHRC, TMC-2, LRO NAC, and SELENE products.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """Geographic bounding box in degrees."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def intersection(self, other: BoundingBox) -> BoundingBox | None:
        """Compute intersection with another bounding box."""
        min_lon = max(self.min_lon, other.min_lon)
        min_lat = max(self.min_lat, other.min_lat)
        max_lon = min(self.max_lon, other.max_lon)
        max_lat = min(self.max_lat, other.max_lat)

        if min_lon < max_lon and min_lat < max_lat:
            return BoundingBox(min_lon, min_lat, max_lon, max_lat)
        return None

    def contains(self, lon: float, lat: float) -> bool:
        return (
            self.min_lon <= lon <= self.max_lon and self.min_lat <= lat <= self.max_lat
        )


@dataclass
class ImageMetadata:
    """Unified metadata representation for any supported lunar image."""

    sensor: str  # 'OHRC', 'TMC-2', 'LRO_NAC', etc.
    width: int
    height: int
    gsd_meters: float  # Ground Sampling Distance (metres/pixel)
    bbox: BoundingBox | None  # Geographic footprint (may be None)
    sun_elevation: float | None = None
    sun_azimuth: float | None = None
    raw_metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], sensor: str = "UNKNOWN") -> ImageMetadata:
        """
        Create ImageMetadata from a standardised dictionary.
        Serves as a generic parser for mock data or normalised JSON.
        """
        bbox = None
        if "bbox" in data:
            b = data["bbox"]
            bbox = BoundingBox(b["min_lon"], b["min_lat"], b["max_lon"], b["max_lat"])

        return cls(
            sensor=data.get("sensor", sensor),
            width=data["width"],
            height=data["height"],
            gsd_meters=data["gsd_meters"],
            bbox=bbox,
            sun_elevation=data.get("sun_elevation"),
            sun_azimuth=data.get("sun_azimuth"),
            raw_metadata=data,
        )


# Future: Add specific parsers for PDS3 labels, XML, GeoTIFF, etc.
# def parse_lro_nac_lbl(filepath: str) -> ImageMetadata: ...
# def parse_ohrc_xml(filepath: str) -> ImageMetadata: ...
