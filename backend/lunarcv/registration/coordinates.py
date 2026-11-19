"""Pixel-center mappings. Matrices act on (x, y, 1) column vectors."""

from dataclasses import dataclass

import numpy as np


def project_points(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    matrix = np.asarray(matrix, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
        raise ValueError("Points must be finite Nx2 pixel coordinates")
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all():
        raise ValueError("Mapping must be a finite 3x3 matrix")
    result = np.column_stack((points, np.ones(len(points)))) @ matrix.T
    if np.any(np.abs(result[:, 2]) < 1e-10):
        raise ValueError("Mapping crosses a projective pole")
    return result[:, :2] / result[:, 2, None]


@dataclass(frozen=True)
class PixelFrame:
    """A resized crop -> native pixels, including OpenCV pixel-center offsets."""

    origin_xy: tuple[float, float] = (0.0, 0.0)
    native_per_processed_xy: tuple[float, float] = (1.0, 1.0)

    @property
    def to_native(self) -> np.ndarray:
        sx, sy = self.native_per_processed_xy
        ox, oy = self.origin_xy
        if min(sx, sy) <= 0 or not np.isfinite([sx, sy, ox, oy]).all():
            raise ValueError("Invalid pixel-frame scale/origin")
        return np.array(
            [[sx, 0, ox + (sx - 1) / 2], [0, sy, oy + (sy - 1) / 2], [0, 0, 1]],
            dtype=np.float64,
        )
