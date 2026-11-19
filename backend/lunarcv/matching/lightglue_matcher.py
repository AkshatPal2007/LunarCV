"""
matching_lightglue.py — Feature matching using DISK/ALIKED + LightGlue for LunarCV.

Wraps official CVG DISK/ALIKED + LightGlue for cross-sensor lunar image matching.
Maintains an identical interface to LoFTRMatcher and RIFT2Matcher.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
import torch
from lightglue import ALIKED, DISK, SIFT, LightGlue
from lightglue.utils import rbd

from lunarcv.matching.matcher import Matcher

logger = logging.getLogger(__name__)


class LightGlueFeatureMatcher(Matcher):
    """
    Wrapper around official CVG DISK/ALIKED + LightGlue for LunarCV.
    Maintains an identical interface to LoFTRMatcher.
    """

    def __init__(
        self,
        device: str | None = None,
        max_dim: int = 1024,
        max_keypoints: int = 2048,
        features: str = "aliked",
    ):
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.max_dim = max_dim
        self.max_keypoints = max_keypoints

        extractors = {"disk": DISK, "aliked": ALIKED, "sift": SIFT}
        if features not in extractors:
            raise ValueError("Release extractor must be disk, aliked, or sift")
        self.features = features
        logger.info("Loading %s extractor on %s", features, self.device)
        self.extractor = (
            extractors[features](max_num_keypoints=self.max_keypoints)
            .to(self.device)
            .eval()
        )
        self.matcher = LightGlue(features=features).to(self.device).eval()
        logger.info(
            "Ready | max_dim=%d | max_keypoints=%d", self.max_dim, max_keypoints
        )

    @torch.no_grad()
    def match(
        self,
        src_u8: np.ndarray,
        ref_u8: np.ndarray,
        conf_threshold: float = 0.0,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Run DISK/ALIKED + LightGlue on a pair of uint8 single-channel images.
        """
        src_proc, scale_src = self._resize_for_matcher(src_u8)
        ref_proc, scale_ref = self._resize_for_matcher(ref_u8)

        def to_tensor(img: np.ndarray) -> torch.Tensor:
            t = (
                torch.from_numpy(img.astype(np.float32) / 255.0)
                .unsqueeze(0)
                .unsqueeze(0)
            )
            return t.to(self.device)

        t_src = to_tensor(src_proc)
        t_ref = to_tensor(ref_proc)

        feats_src = self.extractor.extract(t_src, resize=None)
        feats_ref = self.extractor.extract(t_ref, resize=None)

        matches_dict = self.matcher({"image0": feats_src, "image1": feats_ref})
        feats_src, feats_ref, matches_dict = [
            rbd(x) for x in [feats_src, feats_ref, matches_dict]
        ]

        matches = matches_dict["matches"]  # (K, 2)
        scores = matches_dict.get("scores", None)

        if len(matches) == 0:
            logger.warning("No matches found")
            empty = np.empty((0, 2), dtype=np.float32)
            return empty, empty, np.empty((0,), dtype=np.float32)

        pts_src = feats_src["keypoints"][matches[..., 0]].cpu().numpy()
        pts_ref = feats_ref["keypoints"][matches[..., 1]].cpu().numpy()

        if scores is not None:
            conf = scores.cpu().numpy()
        else:
            raise ValueError("LightGlue output is missing per-match scores")
        if conf.shape != (len(matches),) or not np.isfinite(conf).all():
            raise ValueError("Invalid LightGlue confidence output")

        del t_src, t_ref, feats_src, feats_ref, matches_dict

        if conf_threshold > 0.0:
            mask = conf >= conf_threshold
            pts_src, pts_ref, conf = pts_src[mask], pts_ref[mask], conf[mask]

        mkpts_src = (pts_src + 0.5) * scale_src - 0.5
        mkpts_ref = (pts_ref + 0.5) * scale_ref - 0.5

        logger.info("Matches: %d", len(conf))
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
