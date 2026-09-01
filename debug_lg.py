import sys
import os
import torch
import numpy as np

# Suppress kornia warnings
import warnings
warnings.filterwarnings("ignore")

# Force CPU for debugging to avoid CUDA hangs
device = torch.device("cpu")
print(f"Using device: {device}")

from kornia.feature import ALIKED, LightGlueMatcher
import kornia.feature as kf

print("Loading ALIKED-n16...")
extractor = ALIKED(model_name="aliked-n16", max_num_keypoints=2048, nms_radius=2).to(device).eval()

print("Loading LightGlueMatcher (aliked)...")
matcher = LightGlueMatcher(feature_name="aliked").to(device).eval()

# Create dummy images
img1 = torch.rand(1, 3, 512, 512, device=device)
img2 = torch.rand(1, 3, 512, 512, device=device)

print("Running ALIKED on img1...")
with torch.no_grad():
    feat1 = extractor(img1)
    feat2 = extractor(img2)

f1 = feat1[0]
if isinstance(f1, dict):
    kpts1, desc1 = f1["keypoints"], f1["descriptors"]
else:
    kpts1 = f1.keypoints if hasattr(f1, "keypoints") else f1[0]
    desc1 = f1.descriptors if hasattr(f1, "descriptors") else f1[1]

print(f"Extracted img1: kpts={kpts1.shape}, desc={desc1.shape}")

f2 = feat2[0]
if isinstance(f2, dict):
    kpts2, desc2 = f2["keypoints"], f2["descriptors"]
else:
    kpts2 = f2.keypoints if hasattr(f2, "keypoints") else f2[0]
    desc2 = f2.descriptors if hasattr(f2, "descriptors") else f2[1]

print(f"Extracted img2: kpts={kpts2.shape}, desc={desc2.shape}")

# Build LAFs
lafs1 = kf.laf_from_center_scale_ori(
    kpts1.unsqueeze(0) if kpts1.dim() == 2 else kpts1,
    torch.ones(1, kpts1.shape[-2], 1, 1, device=device),
    torch.zeros(1, kpts1.shape[-2], 1, device=device)
)
lafs2 = kf.laf_from_center_scale_ori(
    kpts2.unsqueeze(0) if kpts2.dim() == 2 else kpts2,
    torch.ones(1, kpts2.shape[-2], 1, 1, device=device),
    torch.zeros(1, kpts2.shape[-2], 1, device=device)
)
print(f"LAFs: lafs1={lafs1.shape}")

hw1 = (512, 512)
hw2 = (512, 512)

# Ensure descriptor shape is (N, D)
d1 = desc1.squeeze(0) if desc1.dim() == 3 else desc1
d2 = desc2.squeeze(0) if desc2.dim() == 3 else desc2

print("Running LightGlueMatcher...")
with torch.no_grad():
    scores, matches = matcher(d1, d2, lafs1, lafs2, hw1=None, hw2=None)

print(f"Matches found: {len(matches)}")

# Print a tiny bit of matches to verify
if len(matches) > 0:
    print(f"Matches slice:\n{matches[:5]}")
else:
    print("NO MATCHES FOUND on random noise (expected if it correctly filters out garbage).")

# Now let's try with identical images!
print("\n--- Testing identical image ---")
with torch.no_grad():
    scores_ident, matches_ident = matcher(d1, d1, lafs1, lafs1, hw1=hw1, hw2=hw1)

print(f"Matches on identical img: {len(matches_ident)}")
