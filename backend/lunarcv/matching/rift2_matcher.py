"""
rift2_matcher.py — RIFT2 phase-congruency feature matcher.
Wraps the third_party RIFT2 implementation into the Matcher interface.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import cv2
import numpy as np

from lunarcv.matching.matcher import Matcher

logger = logging.getLogger(__name__)

# Locate the third_party/rift2 directory relative to this file's package root
_BACKEND_ROOT = Path(__file__).resolve().parent.parent  # backend/lunarcv/
_RIFT2_DIR = _BACKEND_ROOT / "third_party" / "rift2"

if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
if str(_RIFT2_DIR) not in sys.path:
    sys.path.insert(0, str(_RIFT2_DIR))

try:
    from matcher_functions import match_keypoints_nn  # type: ignore
    from RIFT2 import RIFT2  # type: ignore

    _RIFT2_AVAILABLE = True
except ImportError as _e:
    _RIFT2_AVAILABLE = False
    logger.warning(f"RIFT2 not available: {_e}")


class RIFT2Matcher(Matcher):
    """
    Wrapper for RIFT2 (phase-congruency based matcher) for LunarCV.
    Raises ImportError at construction time if RIFT2 is not installed.
    """

    def __init__(self, config_file: str | None = None, **kwargs):
        if not _RIFT2_AVAILABLE:
            raise ImportError(
                "RIFT2 third-party library could not be imported. "
                f"Ensure {_RIFT2_DIR} exists and dependencies are installed."
            )
        self.max_dim = kwargs.pop("max_dim", 1024)
        kwargs.setdefault("npt", 2048)
        self.rift = RIFT2(config_file=config_file, **kwargs)

    def match(
        self,
        src_img: np.ndarray,
        ref_img: np.ndarray,
        conf_threshold: float = 0.0,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Run RIFT2 detection, description, and mutual nearest-neighbour matching."""
        _empty = (
            np.empty((0, 2), dtype=np.float32),
            np.empty((0, 2), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
        )

        def prepare(image):
            h, w = image.shape
            ratio = min(1.0, self.max_dim / max(h, w))
            size = (max(16, round(w * ratio)), max(16, round(h * ratio)))
            return cv2.resize(image, size, interpolation=cv2.INTER_AREA), np.array(
                [w / size[0], h / size[1]]
            )

        src_img, src_scale = prepare(src_img)
        ref_img, ref_scale = prepare(ref_img)
        kp1, des1, kp2, des2 = self.rift(src_img, ref_img)

        if len(kp1) < 2 or len(kp2) < 2 or des1 is None or des2 is None:
            return _empty

        pts_src, pts_ref, _ = match_keypoints_nn(
            des1, des2, kp1, kp2, lowes_ratio=0.8, mutual=True
        )

        n = len(pts_src)
        if n == 0:
            return _empty

        # RIFT2 does not produce learned confidence scores; use 1.0 uniformly.
        conf = np.ones(n, dtype=np.float32)

        if conf_threshold > 0.0:
            mask = conf >= conf_threshold
            pts_src, pts_ref, conf = pts_src[mask], pts_ref[mask], conf[mask]

        return (
            (pts_src + 0.5) * src_scale - 0.5,
            (pts_ref + 0.5) * ref_scale - 0.5,
            conf,
        )
