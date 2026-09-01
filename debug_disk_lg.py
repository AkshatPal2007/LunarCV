import sys
import torch
from kornia.feature import DISK, LightGlueMatcher
import kornia.feature as kf

device = torch.device("cpu")
print("Loading DISK...")
extractor = DISK.from_pretrained("depth").to(device).eval()
matcher = LightGlueMatcher(feature_name="disk").to(device).eval()

img1 = torch.rand(1, 3, 512, 512, device=device)

with torch.no_grad():
    feat1 = extractor(img1)
    
f1 = feat1[0]
if isinstance(f1, dict):
    kpts1, desc1 = f1["keypoints"], f1["descriptors"]
else:
    kpts1 = f1.keypoints if hasattr(f1, "keypoints") else f1[0]
    desc1 = f1.descriptors if hasattr(f1, "descriptors") else f1[1]

print(f"Extracted img1: kpts={kpts1.shape}, desc={desc1.shape}")

lafs1 = kf.laf_from_center_scale_ori(
    kpts1.unsqueeze(0) if kpts1.dim() == 2 else kpts1,
    torch.ones(1, kpts1.shape[-2], 1, 1, device=device),
    torch.zeros(1, kpts1.shape[-2], 1, device=device)
)

d1 = desc1.squeeze(0) if desc1.dim() == 3 else desc1

print("Running LightGlueMatcher with DISK...")
with torch.no_grad():
    scores, matches = matcher(d1, d1, lafs1, lafs1, hw1=None, hw2=None)

print(f"Matches found: {len(matches)}")
