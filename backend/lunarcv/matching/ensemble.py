"""
ensemble.py — Multi-matcher aggregation strategy for LunarCV.
Runs multiple Matcher backends and combines their candidate correspondences.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

import numpy as np

from lunarcv.matching.matcher import Matcher

logger = logging.getLogger(__name__)


class EnsembleMatcher(Matcher):
    """
    Aggregates candidates from multiple Matcher backends.
    Primary use-case: LightGlue (primary) + RIFT2 (fallback on sparse strips).

    Each matcher is called independently; exceptions from any single matcher
    are caught and logged so the ensemble degrades gracefully.
    """

    def __init__(self, matchers: List[Matcher]):
        if not matchers:
            raise ValueError("EnsembleMatcher requires at least one matcher.")
        self.matchers = matchers

    def match(
        self,
        src_img: np.ndarray,
        ref_img: np.ndarray,
        conf_threshold: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Run all matchers and return combined candidates."""
        all_src, all_ref, all_conf = [], [], []

        for matcher in self.matchers:
            try:
                pts_src, pts_ref, conf = matcher.match(src_img, ref_img, conf_threshold)
                if len(pts_src) > 0:
                    all_src.append(pts_src)
                    all_ref.append(pts_ref)
                    all_conf.append(conf)
            except Exception as exc:
                logger.warning(f"Matcher {type(matcher).__name__} failed: {exc}")

        if not all_src:
            return (
                np.empty((0, 2), dtype=np.float32),
                np.empty((0, 2), dtype=np.float32),
                np.empty((0,), dtype=np.float32),
            )

        return (
            np.vstack(all_src),
            np.vstack(all_ref),
            np.concatenate(all_conf),
        )
