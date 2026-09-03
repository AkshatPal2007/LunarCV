"""
matching_lightglue.py — Feature matching using SuperPoint + LightGlue for LunarCV.

Wraps official CVG SuperPoint + LightGlue for cross-sensor lunar image matching.
Maintains an identical interface to LoFTRMatcher and RIFT2Matcher.
"""

from __future__ import annotations

import cv2
import numpy as np
import torch
from lightglue import LightGlue, SuperPoint
from lightglue.utils import rbd


class LightGlueFeatureMatcher:
    """
    Wrapper around official CVG SuperPoint + LightGlue for LunarCV.
    Maintains an identical interface to LoFTRMatcher.
    """
    def __init__(self, device: str | None = None, max_dim: int = 1024, max_keypoints: int = 2048):
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.max_dim = max_dim
        self.max_keypoints = max_keypoints

        print(f"[LightGlue] Loading SuperPoint extractor on {self.device}...")
        self.extractor = SuperPoint(max_num_keypoints=self.max_keypoints).to(self.device).eval()

        print("[LightGlue] Loading LightGlueMatcher(superpoint)...")
        self.matcher = LightGlue(features="superpoint").to(self.device).eval()

        print(f"[LightGlue] Ready | max_dim={self.max_dim} | max_keypoints={max_keypoints}")

    @torch.no_grad()
    def match(
        self,
        src_u8: np.ndarray,
        ref_u8: np.ndarray,
        conf_threshold: float = 0.0,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Run SuperPoint + LightGlue on a pair of uint8 single-channel images.
        """
        src_proc, scale_src = self._resize_for_matcher(src_u8)
        ref_proc, scale_ref = self._resize_for_matcher(ref_u8)

        def to_tensor(img: np.ndarray) -> torch.Tensor:
            t = torch.from_numpy(img.astype(np.float32) / 255.0).unsqueeze(0).unsqueeze(0)
            return t.to(self.device)

        t_src = to_tensor(src_proc)
        t_ref = to_tensor(ref_proc)

        feats_src = self.extractor.extract(t_src)
        feats_ref = self.extractor.extract(t_ref)

        matches_dict = self.matcher({"image0": feats_src, "image1": feats_ref})
        feats_src, feats_ref, matches_dict = [rbd(x) for x in [feats_src, feats_ref, matches_dict]]

        matches = matches_dict["matches"]  # (K, 2)
        scores = matches_dict.get("matching_scores", None)

        if len(matches) == 0:
            print("[LightGlue] No matches found")
            empty = np.empty((0, 2), dtype=np.float32)
            return empty, empty, np.empty((0,), dtype=np.float32)

        pts_src = feats_src["keypoints"][matches[..., 0]].cpu().numpy()
        pts_ref = feats_ref["keypoints"][matches[..., 1]].cpu().numpy()

        if scores is not None:
            conf = scores.cpu().numpy()
        else:
            conf = np.ones(len(matches), dtype=np.float32)

        del t_src, t_ref, feats_src, feats_ref, matches_dict
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
