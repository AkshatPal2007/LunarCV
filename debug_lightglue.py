import sys
sys.path.insert(0, 'src')
from matching_lightglue import LightGlueFeatureMatcher
from io_utils import load_ohrc_memmap, load_lro_nac_memmap, extract_patch
from preprocessing import percentile_stretch_uint8
from config import OHRC_IMG_PATH, LRO_IMG_PATH, OHRC_SHAPE, OHRC_DTYPE, SCALE_RATIO_LRO_TO_OHRC
import cv2
import numpy as np

def test_lightglue():
    ohrc_mm = load_ohrc_memmap(OHRC_IMG_PATH, shape=OHRC_SHAPE, dtype=OHRC_DTYPE)
    lro_mm, _ = load_lro_nac_memmap(LRO_IMG_PATH)
    
    ohrc_raw = extract_patch(ohrc_mm, (30000, 31000), (2000, 3000))
    lro_raw = extract_patch(lro_mm, (5500, 6500), (400, 1400))
    
    ohrc_norm = percentile_stretch_uint8(ohrc_raw)
    lro_norm = percentile_stretch_uint8(lro_raw)
    
    target_w = int(round(ohrc_norm.shape[1] / SCALE_RATIO_LRO_TO_OHRC))
    target_h = int(round(ohrc_norm.shape[0] / SCALE_RATIO_LRO_TO_OHRC))
    ohrc_scaled = cv2.resize(ohrc_norm, (target_w, target_h), interpolation=cv2.INTER_AREA)
    
    matcher = LightGlueFeatureMatcher(max_dim=1024, max_keypoints=2048)
    
    # We will hook into the extractor and matcher inside
    src_proc, scale_src = matcher._resize(ohrc_scaled)
    ref_proc, scale_ref = matcher._resize(lro_norm)

    t_src = matcher._to_tensor(src_proc)
    t_ref = matcher._to_tensor(ref_proc)

    feat_src = matcher.extractor(t_src)
    feat_ref = matcher.extractor(t_ref)
    
    def get_kpts_desc_lafs(feat_list):
        feat = feat_list[0]
        if isinstance(feat, dict):
            kpts = feat["keypoints"]
            desc = feat["descriptors"]
            lafs = feat.get("lafs", None)
        else:
            kpts = feat.keypoints if hasattr(feat, "keypoints") else feat[0]
            desc = feat.descriptors if hasattr(feat, "descriptors") else feat[1]
            lafs = feat.lafs if hasattr(feat, "lafs") else None

        if kpts.dim() == 2:
            kpts = kpts.unsqueeze(0)
        if desc.dim() == 2:
            desc = desc.unsqueeze(0)
            
        return kpts.squeeze(0), desc.squeeze(0), lafs
        
    kpts_src, desc_src, lafs_src = get_kpts_desc_lafs(feat_src)
    kpts_ref, desc_ref, lafs_ref = get_kpts_desc_lafs(feat_ref)
    
    print(f"kpts_src: {kpts_src.shape}")
    print(f"desc_src: {desc_src.shape}")
    print(f"lafs_src: {'None' if lafs_src is None else lafs_src.shape}")
    
    pts_src, pts_ref, conf = matcher.match(ohrc_scaled, lro_norm)
    print(f"Final matches: {len(pts_src)}")

if __name__ == '__main__':
    test_lightglue()
