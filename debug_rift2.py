import cv2
import numpy as np
import sys
sys.path.append('src')
from matching_rift2 import RIFT2Matcher
from matching import load_matching_images, prepare_matching_pair
from matcher_benchmark import load_image_pair
import time

def debug_rift2():
    print("Loading images...")
    src_img, ref_img = load_image_pair()
    print("Running RIFT2 Matcher...")
    matcher = RIFT2Matcher(max_dim=1024)
    
    src_proc, scale_src = matcher._resize_for_matcher(src_img)
    ref_proc, scale_ref = matcher._resize_for_matcher(ref_img)
    
    print("Feature Extraction...")
    t0 = time.time()
    kp_src, desc_src, kp_ref, desc_ref = matcher.model(src_proc, ref_proc)
    print(f"Extracted {len(kp_src)} src and {len(kp_ref)} ref keypoints in {time.time()-t0:.2f}s")
    
    print("Matching without ratio test (just Mutual NN)...")
    pts_src, pts_ref, conf = matcher._match_keypoints_nn(
        desc_src, desc_ref, kp_src, kp_ref, lowes_ratio=1.0, mutual=True
    )
    print(f"Matches found: {len(pts_src)}")
    
    print("Matching with Lowe's ratio=0.85...")
    pts_src, pts_ref, conf = matcher._match_keypoints_nn(
        desc_src, desc_ref, kp_src, kp_ref, lowes_ratio=0.85, mutual=True
    )
    print(f"Matches found: {len(pts_src)}")

if __name__ == "__main__":
    debug_rift2()
