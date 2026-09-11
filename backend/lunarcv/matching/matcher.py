"""
matcher.py — Abstract base class for all LunarCV feature matchers.
"""

from __future__ import annotations

import abc

import numpy as np


class Matcher(abc.ABC):
    """
    Abstract base for all feature-matching backends (LightGlue, RIFT2, etc.).
    Every concrete matcher must implement :meth:`match`.
    """

    @abc.abstractmethod
    def match(
        self,
        src_img: np.ndarray,
        ref_img: np.ndarray,
        conf_threshold: float = 0.0,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract and match features between source and reference images.

        Parameters
        ----------
        src_img : np.ndarray  uint8 grayscale, shape (H, W)
        ref_img : np.ndarray  uint8 grayscale, shape (H, W)
        conf_threshold : float  Discard matches with confidence < threshold.

        Returns
        -------
        pts_src : (N, 2) float32  source coordinates (x, y)
        pts_ref : (N, 2) float32  reference coordinates (x, y)
        confidence : (N,) float32  per-match confidence
        """
