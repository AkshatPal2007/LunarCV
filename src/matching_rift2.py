"""
matching_rift2.py — Feature matching using RIFT2 (Phase Congruency) for LunarCV.

Wraps the third-party RIFT2 implementation and exposes the standard
LunarCV matching interface (similar to LoFTRMatcher).
"""

from __future__ import annotations

import cv2
import numpy as np
from third_party.rift2.RIFT2 import RIFT2


class RIFT2Matcher:
    """
    Wrapper around RIFT2 for LunarCV.
    Maintains an identical interface to LoFTRMatcher.
    """
    def __init__(self, max_dim: int = 1024):
        self.max_dim = max_dim
        # Initialize RIFT2 without relying on a config file to simplify deployment
        self.model = RIFT2(npt=5000)
        print(f"[RIFT2] Loaded RIFT2 (Phase Congruency) | max_dim={self.max_dim}")

    def match(
        self,
        src_u8: np.ndarray,
        ref_u8: np.ndarray,
        conf_threshold: float = 0.0
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Run RIFT2 on a pair of uint8 single-channel images.
        """
        src_proc, scale_src = self._resize_for_matcher(src_u8)
        ref_proc, scale_ref = self._resize_for_matcher(ref_u8)

        # RIFT2 processes the features (outputs list of cv2.KeyPoint and descriptors)
        kp_src, desc_src, kp_ref, desc_ref = self.model(src_proc, ref_proc)
        
        if len(kp_src) < 2 or len(kp_ref) < 2:
            print("[RIFT2] Too few keypoints to match")
            empty = np.empty((0, 2), dtype=np.float32)
            return empty, empty, np.empty((0,), dtype=np.float32)

        # Match keypoints using BFMatcher (Mutual Nearest Neighbors only, no ratio test)
        pts_src, pts_ref, conf = self._match_keypoints_nn(
            desc_src, desc_ref, kp_src, kp_ref, lowes_ratio=1.0, mutual=True
        )

        if len(pts_src) == 0:
            print("[RIFT2] No matches found after ratio test")
            empty = np.empty((0, 2), dtype=np.float32)
            return empty, empty, np.empty((0,), dtype=np.float32)
            
        if conf_threshold > 0.0:
            mask = conf >= conf_threshold
            pts_src, pts_ref, conf = pts_src[mask], pts_ref[mask], conf[mask]

        # Rescale coordinates back to the original image dimensions
        mkpts_src = pts_src * scale_src
        mkpts_ref = pts_ref * scale_ref

        print(f"[RIFT2] Matches: {len(conf)}")
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
        
    def _match_keypoints_nn(self, des1, des2, kp1, kp2, lowes_ratio=0.75, mutual=True):
        bf = cv2.BFMatcher()

        # Mutual Nearest Neighbor Matching
        matches1 = bf.knnMatch(des1, des2, k=2)

        if mutual:
            matches2 = bf.knnMatch(des2, des1, k=2)
            # Apply ratio test version 2 (mutual nearest neighbor check)
            good_matches1 = []
            for m, n in matches1:
                if m.distance < lowes_ratio * n.distance:
                    good_matches1.append(m)

            good_matches2 = []
            for m, n in matches2:
                if m.distance < lowes_ratio * n.distance:
                    good_matches2.append(m)

            # Mutual Nearest Neighbor
            mutual_matches = []
            for m in good_matches1:
                if any(m.queryIdx == n.trainIdx and m.trainIdx == n.queryIdx for n in good_matches2):
                    mutual_matches.append(m)
        else:
            # Apply ratio test version 1
            mutual_matches = []
            for m, n in matches1:
                if m.distance < lowes_ratio * n.distance:
                    mutual_matches.append(m)

        if len(mutual_matches) == 0:
            return np.empty((0, 2)), np.empty((0, 2)), np.empty(0)

        # Extract location of good matches
        points1 = np.float32([kp1[m.queryIdx].pt for m in mutual_matches]).reshape(-1, 2)
        points2 = np.float32([kp2[m.trainIdx].pt for m in mutual_matches]).reshape(-1, 2)
        
        # We define confidence as (1.0 - ratio) so lower distance ratio = higher confidence
        confidences = np.float32([
            (1.0 - (m.distance / (n.distance + 1e-6))) 
            for m, n in [matches1[m.queryIdx] for m in mutual_matches]
        ])

        return points1, points2, confidences
