import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np


@dataclass
class LunarImage:
    """Represents a lunar image with metadata"""

    path: Path
    data: np.ndarray | None = None

    # Metadata from header
    sensor: str | None = None  # OHRC, TMC-2, IIRS, LRO_NAC, etc.
    mission: str | None = None  # Chandrayaan-2, LRO, SELENE
    gsd: float | None = None  # ground sample distance in meters/pixel

    # Geographic bounds (decimal degrees)
    lon_min: float | None = None
    lon_max: float | None = None
    lat_min: float | None = None
    lat_max: float | None = None

    # Illumination
    sun_azimuth: float | None = None
    sun_elevation: float | None = None

    # Processing state
    normalized: bool = False

    def save(self, output_dir: Path) -> Path:
        """Save image data and metadata"""
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = self.path.stem

        # Save array
        if self.data is not None:
            np.savez_compressed(output_dir / f"{stem}_data.npz", image=self.data)

        # Save metadata
        metadata = {
            "path": str(self.path),
            "sensor": self.sensor,
            "mission": self.mission,
            "gsd": self.gsd,
            "lon_min": self.lon_min,
            "lon_max": self.lon_max,
            "lat_min": self.lat_min,
            "lat_max": self.lat_max,
            "sun_azimuth": self.sun_azimuth,
            "sun_elevation": self.sun_elevation,
            "normalized": self.normalized,
        }

        meta_path = output_dir / f"{stem}_meta.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return meta_path

    @classmethod
    def load(cls, meta_path: Path) -> "LunarImage":
        """Load image from saved metadata + data"""
        with open(meta_path) as f:
            metadata = json.load(f)

        # Load array if exists
        data_path = meta_path.parent / meta_path.name.replace("_meta.json", "_data.npz")
        data = None
        if data_path.exists():
            with np.load(data_path) as npz:
                data = npz["image"]

        return cls(
            path=Path(metadata["path"]),
            data=data,
            sensor=metadata["sensor"],
            mission=metadata["mission"],
            gsd=metadata["gsd"],
            lon_min=metadata["lon_min"],
            lon_max=metadata["lon_max"],
            lat_min=metadata["lat_min"],
            lat_max=metadata["lat_max"],
            sun_azimuth=metadata["sun_azimuth"],
            sun_elevation=metadata["sun_elevation"],
            normalized=metadata["normalized"],
        )


@dataclass
class MatchSet:
    """Keypoint matches between source and reference images"""

    source_name: str
    reference_name: str

    # Keypoints (Nx2 arrays)
    source_kpts: np.ndarray
    reference_kpts: np.ndarray

    # Match metadata
    matcher_type: str  # "lightglue", "rift2", "ensemble"
    confidence: np.ndarray | None = None  # per-match confidence scores

    # Outlier rejection
    inlier_mask: np.ndarray | None = None
    transform_type: str | None = None  # "similarity", "affine", "homography"

    @property
    def n_matches(self) -> int:
        return len(self.source_kpts)

    @property
    def n_inliers(self) -> int:
        if self.inlier_mask is None:
            return self.n_matches
        return int(self.inlier_mask.sum())

    @property
    def inlier_ratio(self) -> float:
        if self.n_matches == 0:
            return 0.0
        return self.n_inliers / self.n_matches

    def save(self, output_dir: Path) -> Path:
        """Save matches"""
        output_dir.mkdir(parents=True, exist_ok=True)

        stem = f"matches_{self.source_name}_{self.reference_name}"

        # Save arrays
        arrays: dict[str, Any] = {
            "source_kpts": self.source_kpts,
            "reference_kpts": self.reference_kpts,
        }
        if self.confidence is not None:
            arrays["confidence"] = self.confidence
        if self.inlier_mask is not None:
            arrays["inlier_mask"] = self.inlier_mask

        np.savez_compressed(output_dir / f"{stem}.npz", **arrays)

        # Save metadata
        metadata = {
            "source_name": self.source_name,
            "reference_name": self.reference_name,
            "matcher_type": self.matcher_type,
            "transform_type": self.transform_type,
            "n_matches": self.n_matches,
            "n_inliers": self.n_inliers,
            "inlier_ratio": self.inlier_ratio,
        }

        meta_path = output_dir / f"{stem}_meta.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return meta_path

    @classmethod
    def load(cls, meta_path: Path) -> "MatchSet":
        """Load matches from saved files"""
        with open(meta_path) as f:
            metadata = json.load(f)

        # Load arrays
        data_path = meta_path.parent / meta_path.name.replace("_meta.json", ".npz")
        with np.load(data_path) as npz:
            source_kpts = npz["source_kpts"]
            reference_kpts = npz["reference_kpts"]
            confidence = npz.get("confidence", None)
            inlier_mask = npz.get("inlier_mask", None)

        return cls(
            source_name=metadata["source_name"],
            reference_name=metadata["reference_name"],
            source_kpts=source_kpts,
            reference_kpts=reference_kpts,
            matcher_type=metadata["matcher_type"],
            confidence=confidence,
            inlier_mask=inlier_mask,
            transform_type=metadata["transform_type"],
        )


@dataclass
class TransformModel:
    """Geometric transform from source to reference frame"""

    transform_type: Literal["similarity", "affine", "homography", "tps"]
    matrix: np.ndarray | None = None  # 3x3 for homography/affine

    # TPS control points (if transform_type == "tps")
    source_control: np.ndarray | None = None
    reference_control: np.ndarray | None = None

    # Residuals
    mean_error: float | None = None
    rmse: float | None = None

    def save(self, output_dir: Path, name: str) -> Path:
        """Save transform"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save arrays
        arrays = {}
        if self.matrix is not None:
            arrays["matrix"] = self.matrix
        if self.source_control is not None:
            arrays["source_control"] = self.source_control
        if self.reference_control is not None:
            arrays["reference_control"] = self.reference_control

        if arrays:
            np.savez_compressed(output_dir / f"{name}.npz", **arrays)

        # Save metadata
        metadata = {
            "transform_type": self.transform_type,
            "mean_error": self.mean_error,
            "rmse": self.rmse,
        }

        meta_path = output_dir / f"{name}_meta.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return meta_path

    @classmethod
    def load(cls, meta_path: Path) -> "TransformModel":
        """Load transform from saved files"""
        with open(meta_path) as f:
            metadata = json.load(f)

        # Load arrays
        data_path = meta_path.parent / meta_path.name.replace("_meta.json", ".npz")
        matrix = None
        source_control = None
        reference_control = None

        if data_path.exists():
            with np.load(data_path) as npz:
                matrix = npz.get("matrix", None)
                source_control = npz.get("source_control", None)
                reference_control = npz.get("reference_control", None)

        return cls(
            transform_type=metadata["transform_type"],
            matrix=matrix,
            source_control=source_control,
            reference_control=reference_control,
            mean_error=metadata["mean_error"],
            rmse=metadata["rmse"],
        )


@dataclass
class RegistrationResult:
    """Complete registration result"""

    source_name: str
    reference_name: str

    # Registered image
    registered: np.ndarray

    # Transform used
    transform: TransformModel

    # Matches used
    matches: MatchSet

    def save(self, output_dir: Path) -> Path:
        """Save registration result"""
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"registered_{self.source_name}_to_{self.reference_name}"

        # Save registered image
        np.savez_compressed(output_dir / f"{stem}.npz", registered=self.registered)

        # Save transform and matches
        self.transform.save(output_dir, f"{stem}_transform")
        self.matches.save(output_dir)

        # Save metadata
        metadata = {
            "source_name": self.source_name,
            "reference_name": self.reference_name,
        }

        meta_path = output_dir / f"{stem}_meta.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return meta_path

    @classmethod
    def load(cls, meta_path: Path) -> "RegistrationResult":
        """Load registration result"""
        with open(meta_path) as f:
            metadata = json.load(f)

        stem = meta_path.stem.replace("_meta", "")

        # Load registered image
        with np.load(meta_path.parent / f"{stem}.npz") as npz:
            registered = npz["registered"]

        # Load transform and matches
        transform = TransformModel.load(
            meta_path.parent / f"{stem}_transform_meta.json"
        )

        match_meta = (
            meta_path.parent
            / f"matches_{metadata['source_name']}_{metadata['reference_name']}_meta.json"
        )
        matches = MatchSet.load(match_meta)

        return cls(
            source_name=metadata["source_name"],
            reference_name=metadata["reference_name"],
            registered=registered,
            transform=transform,
            matches=matches,
        )


@dataclass
class EvaluationMetrics:
    """Evaluation metrics for registration quality"""

    source_name: str
    reference_name: str

    # Match quality
    n_matches: int
    n_inliers: int
    inlier_ratio: float

    # Geometric accuracy
    rmse: float
    mean_error: float
    max_error: float | None = None

    # Spatial distribution (CV = coefficient of variation)
    spatial_uniformity_cv: float | None = None

    # Execution time (seconds)
    matching_time: float | None = None
    registration_time: float | None = None
    total_time: float | None = None

    def save(self, output_dir: Path) -> Path:
        """Save metrics"""
        output_dir.mkdir(parents=True, exist_ok=True)

        stem = f"metrics_{self.source_name}_{self.reference_name}"
        meta_path = output_dir / f"{stem}.json"

        with open(meta_path, "w") as f:
            json.dump(self.__dict__, f, indent=2)

        return meta_path

    @classmethod
    def load(cls, meta_path: Path) -> "EvaluationMetrics":
        """Load metrics"""
        with open(meta_path) as f:
            data = json.load(f)
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for reporting"""
        return self.__dict__
