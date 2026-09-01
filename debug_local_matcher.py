import sys
import torch
from kornia.feature import ALIKED, LightGlueMatcher, LocalFeatureMatcher

device = torch.device("cpu")
print("Loading ALIKED and LightGlue...")
extractor = ALIKED(model_name="aliked-n16", max_num_keypoints=2048, nms_radius=2).to(device).eval()
matcher = LightGlueMatcher(feature_name="aliked").to(device).eval()
local_matcher = LocalFeatureMatcher(extractor, matcher).to(device).eval()

img1 = torch.rand(1, 1, 512, 512, device=device) # ALIKED accepts 1 channel? Wait, Kornia ALIKED needs 3 channels?
img1_3c = img1.repeat(1, 3, 1, 1)

print("Running LocalFeatureMatcher...")
try:
    with torch.no_grad():
        out = local_matcher({"image0": img1_3c, "image1": img1_3c})
    
    print(f"Matches found: {len(out['matches0'])}")
except Exception as e:
    print(f"Exception: {e}")
