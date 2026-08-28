"""
matching.py — Feature matching utilities for LunarCV.

Wraps detector-free LoFTR (Kornia) for cross-sensor lunar image matching.

IMPORTANT — VRAM budget:
    LoFTR was designed for ~640×480 images. On an 8 GB GPU, feeding 4000×2000
    images directly causes CUDA OOM. This class automatically downscales the
    images to max_dim (default 840) before running LoFTR, then rescales the
    keypoint coordinates back to the original image space. Matching quality is
    not affected — the scale factor is tracked and applied precisely.

Usage:
    from matching import LoFTRMatcher
    matcher = LoFTRMatcher()                     # uses CUDA if available
    mkpts_src, mkpts_ref, conf = matcher.match(src_u8, ref_u8)
"""

from __future__ import annotations

import cv2
import numpy as np
import torch
from kornia.feature import LoFTR


class LoFTRMatcher:
    """
    Wrapper around Kornia LoFTR for LunarCV.

    Parameters
    ----------
    pretrained : str
        'outdoor' (default) — handles large low-texture terrain; correct for lunar.
        'indoor' — smaller scenes with more texture detail.
    device : str | None
        'cuda', 'cpu', or None (auto-selects CUDA if available).
    max_dim : int
        Maximum image dimension for LoFTR inference (default 840).
        Images are downscaled so max(H, W) <= max_dim before matching.
        Keypoints are then rescaled back to original image space.
        Reduce to 640 if you still get OOM; increase toward 1024 if GPU allows.
    """

    def __init__(
        self,
        pretrained: str = "outdoor",
        device: str | None = None,
        max_dim: int = 840,
    ):
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.max_dim = max_dim
        self.model = LoFTR(pretrained=pretrained).to(self.device).eval()
        print(f"[LoFTR] Loaded '{pretrained}' on {self.device} | max_dim={self.max_dim}")

    @torch.no_grad()
    def match(
        self,
        src_u8: np.ndarray,
        ref_u8: np.ndarray,
        conf_threshold: float = 0.5,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Run LoFTR on a pair of uint8 single-channel images.

        Parameters
        ----------
        src_u8 : ndarray (H, W), dtype uint8
            Source (Chandrayaan-2 TMC-2) preprocessed patch.
        ref_u8 : ndarray (H, W), dtype uint8
            Reference (LRO NAC) preprocessed patch.
        conf_threshold : float
            Drop matches below this confidence (default 0.5).

        Returns
        -------
        mkpts_src : ndarray (N, 2)  — (x, y) in original source image space
        mkpts_ref : ndarray (N, 2)  — (x, y) in original reference image space
        conf      : ndarray (N,)    — confidence scores [0, 1]
        """
        # Downscale to max_dim (LoFTR designed for ~640-840 px images)
        src_proc, scale_src = self._resize_for_loftr(src_u8)
        ref_proc, scale_ref = self._resize_for_loftr(ref_u8)
        print(f"[LoFTR] src {src_u8.shape} -> {src_proc.shape}, "
              f"ref {ref_u8.shape} -> {ref_proc.shape}")

        def to_tensor(img: np.ndarray) -> torch.Tensor:
            return (torch.from_numpy(img.astype(np.float32) / 255.0)
                    .unsqueeze(0).unsqueeze(0).to(self.device))

        batch = {"image0": to_tensor(src_proc), "image1": to_tensor(ref_proc)}
        out = self.model(batch)  # returns a NEW dict containing keypoints0, keypoints1, confidence

        pts_src = out["keypoints0"].cpu().numpy()   # (N, 2) — fine-level matches in image0
        pts_ref = out["keypoints1"].cpu().numpy()   # (N, 2) — fine-level matches in image1
        conf    = out["confidence"].cpu().numpy()   # (N,)

        # Free GPU memory immediately
        del batch, out
        torch.cuda.empty_cache()

        # Filter by confidence
        if conf_threshold > 0.0:
            mask  = conf >= conf_threshold
            pts_src = pts_src[mask]
            pts_ref = pts_ref[mask]
            conf    = conf[mask]

        # Rescale keypoints back to original image coordinate space
        mkpts_src = pts_src * scale_src   # (N, 2)
        mkpts_ref = pts_ref * scale_ref   # (N, 2)

        print(f"[LoFTR] Matches: {len(conf)} (conf >= {conf_threshold})")
        return mkpts_src, mkpts_ref, conf

    def _resize_for_loftr(self, img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Downscale img so max(H, W) <= self.max_dim, keeping dims multiples of 8
        (required by LoFTR's coarse feature grid).

        Returns (resized_img, scale_xy) where scale_xy maps resized -> original.
        """
        h, w = img.shape
        scale_ratio = min(1.0, self.max_dim / max(h, w))
        new_w = max(8, int(w * scale_ratio // 8) * 8)
        new_h = max(8, int(h * scale_ratio // 8) * 8)

        if new_w == w and new_h == h:
            return img, np.ones(2, dtype=np.float32)

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        scale_xy = np.array([w / new_w, h / new_h], dtype=np.float32)
        return resized, scale_xy
