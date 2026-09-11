"""Frozen evaluation manifest and deterministic run provenance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA_VERSION = "1.0"
PROTOCOL_VERSION = "priority-0-v1"


@dataclass(frozen=True)
class EvaluationPair:
    """A scene-level evaluation pair from the frozen manifest."""

    pair_id: str
    split: str
    source_sensor: str
    reference_sensor: str
    source_product_id: str
    reference_product_id: str
    source_path: str
    reference_path: str
    source_shape: tuple[int, int]
    reference_shape: tuple[int, int]
    source_gsd_m: tuple[float, float]
    reference_gsd_m: tuple[float, float]
    source_footprint: dict[str, float]
    reference_footprint: dict[str, float]
    ground_truth_method: str
    ground_truth_status: str


@dataclass(frozen=True)
class EvaluationManifest:
    """Versioned evaluation contract loaded from JSON."""

    manifest_version: str
    protocol_version: str
    seed: int
    pair_split_unit: str
    metrics: dict[str, Any]
    pairs: tuple[EvaluationPair, ...]

    @classmethod
    def load(cls, path: Path) -> EvaluationManifest:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("manifest_version") != MANIFEST_SCHEMA_VERSION:
            raise ValueError("Unsupported evaluation manifest version")
        if payload.get("pair_split_unit") != "scene":
            raise ValueError("Evaluation pairs must be split at scene level")

        pairs = tuple(
            EvaluationPair(
                pair_id=item["pair_id"],
                split=item["split"],
                source_sensor=item["source_sensor"],
                reference_sensor=item["reference_sensor"],
                source_product_id=item["source_product_id"],
                reference_product_id=item["reference_product_id"],
                source_path=item["source_path"],
                reference_path=item["reference_path"],
                source_shape=tuple(item["source_shape"]),
                reference_shape=tuple(item["reference_shape"]),
                source_gsd_m=tuple(item["source_gsd_m"]),
                reference_gsd_m=tuple(item["reference_gsd_m"]),
                source_footprint=dict(item["source_footprint"]),
                reference_footprint=dict(item["reference_footprint"]),
                ground_truth_method=item["ground_truth_method"],
                ground_truth_status=item["ground_truth_status"],
            )
            for item in payload.get("pairs", [])
        )
        if not pairs:
            raise ValueError("Evaluation manifest must contain at least one pair")
        return cls(
            manifest_version=payload["manifest_version"],
            protocol_version=payload["protocol_version"],
            seed=int(payload["seed"]),
            pair_split_unit=payload["pair_split_unit"],
            metrics=dict(payload["metrics"]),
            pairs=pairs,
        )

    def pair(self, pair_id: str) -> EvaluationPair:
        for pair in self.pairs:
            if pair.pair_id == pair_id:
                return pair
        raise KeyError(f"Unknown evaluation pair: {pair_id}")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return a stable content hash without loading a large image into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def build_run_provenance(
    *,
    manifest: EvaluationManifest,
    source_path: Path,
    reference_path: Path,
    source_shape: tuple[int, int],
    reference_shape: tuple[int, int],
    matcher: str,
    parameters: dict[str, Any],
    pair_id: str | None = None,
) -> dict[str, Any]:
    """Create auditable provenance for one run.

    Unknown uploads are deliberately marked ``unregistered`` instead of being
    silently treated as official evaluation data.
    """
    pair = manifest.pair(pair_id) if pair_id is not None else None
    return {
        "manifest_version": manifest.manifest_version,
        "protocol_version": manifest.protocol_version,
        "pair_id": pair.pair_id if pair else None,
        "dataset_split": pair.split if pair else "unregistered",
        "pair_split_unit": manifest.pair_split_unit,
        "source": {
            "path": str(source_path),
            "sha256": sha256_file(source_path),
            "shape": list(source_shape),
            "sensor": pair.source_sensor if pair else None,
            "product_id": pair.source_product_id if pair else None,
        },
        "reference": {
            "path": str(reference_path),
            "sha256": sha256_file(reference_path),
            "shape": list(reference_shape),
            "sensor": pair.reference_sensor if pair else None,
            "product_id": pair.reference_product_id if pair else None,
        },
        "matcher": matcher,
        "parameters": parameters,
        "ground_truth": {
            "method": pair.ground_truth_method if pair else None,
            "status": pair.ground_truth_status if pair else "not_registered",
        },
    }


def manifest_as_dict(manifest: EvaluationManifest) -> dict[str, Any]:
    """Serialize a loaded manifest for inclusion in reports."""
    return {
        "manifest_version": manifest.manifest_version,
        "protocol_version": manifest.protocol_version,
        "seed": manifest.seed,
        "pair_split_unit": manifest.pair_split_unit,
        "metrics": manifest.metrics,
        "pairs": [asdict(pair) for pair in manifest.pairs],
    }
