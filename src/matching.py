"""
matching.py — Feature matching utilities and I/O for LunarCV.

Wraps detector-free LoFTR (Kornia) and provides experiment-agnostic
I/O functions to save/load matches without re-running the heavy neural net.
"""

from __future__ import annotations

import cv2
import numpy as np
import torch
from pathlib import Path
from kornia.feature import LoFTR

from io_utils import load_ohrc_memmap, load_lro_nac_memmap, extract_patch
from preprocessing import percentile_stretch_uint8


class LoFTRMatcher:
    """
    Wrapper around Kornia LoFTR for LunarCV.
    """
    def __init__(self, pretrained: str = "outdoor", device: str | None = None, max_dim: int = 840):
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.max_dim = max_dim
        self.model = LoFTR(pretrained=pretrained).to(self.device).eval()
        print(f"[LoFTR] Loaded '{pretrained}' on {self.device} | max_dim={self.max_dim}")

    @torch.no_grad()
    def match(self, src_u8: np.ndarray, ref_u8: np.ndarray, conf_threshold: float = 0.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        src_proc, scale_src = self._resize_for_loftr(src_u8)
        ref_proc, scale_ref = self._resize_for_loftr(ref_u8)

        def to_tensor(img: np.ndarray) -> torch.Tensor:
            return (torch.from_numpy(img.astype(np.float32) / 255.0)
                    .unsqueeze(0).unsqueeze(0).to(self.device))

        batch = {"image0": to_tensor(src_proc), "image1": to_tensor(ref_proc)}
        out = self.model(batch)

        pts_src = out["keypoints0"].cpu().numpy()
        pts_ref = out["keypoints1"].cpu().numpy()
        conf    = out["confidence"].cpu().numpy()

        del batch, out
        torch.cuda.empty_cache()

        if conf_threshold > 0.0:
            mask = conf >= conf_threshold
            pts_src, pts_ref, conf = pts_src[mask], pts_ref[mask], conf[mask]

        mkpts_src = pts_src * scale_src
        mkpts_ref = pts_ref * scale_ref

        print(f"[LoFTR] Matches: {len(conf)}")
        return mkpts_src, mkpts_ref, conf

    def _resize_for_loftr(self, img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        h, w = img.shape
        scale_ratio = min(1.0, self.max_dim / max(h, w))
        new_w = max(8, int(w * scale_ratio // 8) * 8)
        new_h = max(8, int(h * scale_ratio // 8) * 8)
        if new_w == w and new_h == h:
            return img, np.ones(2, dtype=np.float32)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        scale_xy = np.array([w / new_w, h / new_h], dtype=np.float32)
        return resized, scale_xy


def load_matching_images(
    src_path: Path,
    ref_path: Path,
    src_patch_bounds: tuple[tuple[int, int], tuple[int, int]],
    ref_patch_bounds: tuple[tuple[int, int], tuple[int, int]]
) -> tuple[np.ndarray, np.ndarray]:
    """Load raw image patches from memory-mapped files."""
    src_mm = load_ohrc_memmap(src_path)
    ref_mm, _ = load_lro_nac_memmap(ref_path)
    
    src_raw = extract_patch(src_mm, src_patch_bounds[0], src_patch_bounds[1])
    ref_raw = extract_patch(ref_mm, ref_patch_bounds[0], ref_patch_bounds[1])
    return src_raw, ref_raw


def prepare_matching_pair(
    src_raw: np.ndarray,
    ref_raw: np.ndarray,
    scale_ratio: float
) -> tuple[np.ndarray, np.ndarray]:
    """Apply percentile stretching and target scale alignment."""
    src_norm = percentile_stretch_uint8(src_raw)
    ref_norm = percentile_stretch_uint8(ref_raw)
    
    target_w = int(round(src_norm.shape[1] / scale_ratio))
    target_h = int(round(src_norm.shape[0] / scale_ratio))
    src_scaled = cv2.resize(src_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)
    
    return src_scaled, ref_norm


def filter_match_confidence(
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    conf: np.ndarray,
    threshold: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Filter candidate matches by minimum confidence."""
    mask = conf >= threshold
    return pts_src[mask], pts_ref[mask], conf[mask]


def save_matches_npz(
    filepath: Path,
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    conf: np.ndarray,
    metadata: dict = None
) -> None:
    """Save raw matches and metadata to an NPZ file."""
    save_dict = {
        "pts_src": pts_src.astype(np.float32),
        "pts_ref": pts_ref.astype(np.float32),
        "conf": conf.astype(np.float32)
    }
    if metadata:
        # Save metadata as a 0-d object array of a JSON string or dict
        save_dict["metadata"] = np.array(metadata, dtype=object)
    
    np.savez_compressed(filepath, **save_dict)


def load_matches_npz(filepath: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict | None]:
    """Load matches and metadata from an NPZ file."""
    data = np.load(filepath, allow_pickle=True)
    metadata = data["metadata"].item() if "metadata" in data else None
    return data["pts_src"], data["pts_ref"], data["conf"], metadata
