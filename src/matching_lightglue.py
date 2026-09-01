"""
matching_lightglue.py — Feature matching using DISK + LightGlue (Kornia) for LunarCV.

Wraps detector-based LightGlue for cross-sensor lunar image matching.
Extracts DISK local features and matches them with LightGlue.
Downscales images to a VRAM-safe resolution before matching.
"""

from __future__ import annotations

import cv2
import numpy as np
import torch
import kornia.feature as kf
from kornia.feature import DISK, LightGlueMatcher


class LightGlueFeatureMatcher:
    """
    Wrapper around Kornia DISK + LightGlue for LunarCV.
    Maintains an identical interface to LoFTRMatcher.
    """
    def __init__(self, device: str | None = None, max_dim: int = 1024, max_keypoints: int = 2048):
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.max_dim = max_dim
        self.max_keypoints = max_keypoints
        
        print(f"[LightGlue] Loading DISK extractor on {self.device}...")
        self.extractor = DISK.from_pretrained("depth").to(self.device).eval()
            
        print("[LightGlue] Loading LightGlueMatcher(disk)...")
        self.matcher = LightGlueMatcher(feature_name="disk").to(self.device).eval()
        
        print(f"[LightGlue] Ready | max_dim={self.max_dim} | max_keypoints={max_keypoints}")

    @torch.no_grad()
    def match(
        self,
        src_u8: np.ndarray,
        ref_u8: np.ndarray,
        conf_threshold: float = 0.0
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Run DISK + LightGlue on a pair of uint8 single-channel images.
        """
        src_proc, scale_src = self._resize_for_matcher(src_u8)
        ref_proc, scale_ref = self._resize_for_matcher(ref_u8)

        def to_tensor(img: np.ndarray) -> torch.Tensor:
            t = torch.from_numpy(img.astype(np.float32) / 255.0).unsqueeze(0).unsqueeze(0)
            t = t.repeat(1, 3, 1, 1) # DISK requires 3 channels
            return t.to(self.device)

        t_src = to_tensor(src_proc)
        t_ref = to_tensor(ref_proc)

        # 1. Extract features
        features_src = self.extractor(t_src)
        features_ref = self.extractor(t_ref)
        
        def extract_kpts_desc(features):
            f = features[0]
            if isinstance(f, dict):
                kpts = f["keypoints"]
                desc = f["descriptors"]
            else:
                kpts = f.keypoints if hasattr(f, "keypoints") else f[0]
                desc = f.descriptors if hasattr(f, "descriptors") else f[1]

            if kpts.dim() == 2:
                kpts = kpts.unsqueeze(0)
            if desc.dim() == 2:
                desc = desc.unsqueeze(0)
            
            # Limit to max_keypoints
            if kpts.shape[1] > self.max_keypoints:
                kpts = kpts[:, :self.max_keypoints, :]
                desc = desc[:, :self.max_keypoints, :]
                
            return kpts.squeeze(0), desc.squeeze(0)

        kpts_src, desc_src = extract_kpts_desc(features_src)
        kpts_ref, desc_ref = extract_kpts_desc(features_ref)
        
        if len(kpts_src) < 2 or len(kpts_ref) < 2:
            print("[LightGlue] Too few keypoints to match")
            empty = np.empty((0, 2), dtype=np.float32)
            return empty, empty, np.empty((0,), dtype=np.float32)
            
        lafs_src = kf.laf_from_center_scale_ori(
            kpts_src.unsqueeze(0),
            torch.ones(1, kpts_src.shape[0], 1, 1, device=self.device),
            torch.zeros(1, kpts_src.shape[0], 1, device=self.device)
        )
        lafs_ref = kf.laf_from_center_scale_ori(
            kpts_ref.unsqueeze(0),
            torch.ones(1, kpts_ref.shape[0], 1, 1, device=self.device),
            torch.zeros(1, kpts_ref.shape[0], 1, device=self.device)
        )
        
        # 2. Match features using LightGlueMatcher
        scores, matches = self.matcher(
            desc_src, desc_ref, lafs_src, lafs_ref, hw1=None, hw2=None
        )
        
        if len(matches) == 0:
            print("[LightGlue] No matches found")
            empty = np.empty((0, 2), dtype=np.float32)
            return empty, empty, np.empty((0,), dtype=np.float32)
        
        # matches is (M, 2) where col 0 is idx in src, col 1 is idx in ref
        idx_src = matches[:, 0]
        idx_ref = matches[:, 1]
        
        pts_src = kpts_src[idx_src].cpu().numpy()
        pts_ref = kpts_ref[idx_ref].cpu().numpy()
        conf = scores.squeeze(-1).cpu().numpy()

        del t_src, t_ref, features_src, features_ref, scores, matches
        if self.device.type == "cuda":
            torch.cuda.empty_cache()

        if conf_threshold > 0.0:
            mask = conf >= conf_threshold
            pts_src, pts_ref, conf = pts_src[mask], pts_ref[mask], conf[mask]

        mkpts_src = pts_src * scale_src
        mkpts_ref = pts_ref * scale_ref

        print(f"[LightGlue] Matches: {len(conf)}")
        return mkpts_src, mkpts_ref, conf

    def _resize_for_matcher(self, img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        h, w = img.shape
        scale_ratio = min(1.0, self.max_dim / max(h, w))
        new_w = max(16, int(w * scale_ratio // 16) * 16)
        new_h = max(16, int(h * scale_ratio // 16) * 16)
        if new_w == w and new_h == h:
            return img, np.ones(2, dtype=np.float32)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        scale_xy = np.array([w / new_w, h / new_h], dtype=np.float32)
        return resized, scale_xy
