import cv2
import numpy as np

mkpts_src = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_src.npy')
mkpts_ref = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_ref.npy')

keep_mask = np.ones(len(mkpts_ref), dtype=bool)
for i in range(len(mkpts_ref)):
    if not keep_mask[i]: continue
    d1 = np.linalg.norm(mkpts_src - mkpts_src[i], axis=1)
    d2 = np.linalg.norm(mkpts_ref - mkpts_ref[i], axis=1)
    close_idx = np.where((d1 < 5.0) | (d2 < 5.0))[0]
    for j in close_idx:
        if j != i: keep_mask[j] = False

mkpts_src_clean = mkpts_src[keep_mask]
mkpts_ref_clean = mkpts_ref[keep_mask]

def normalize_pts(pts):
    pts_min = pts.min(axis=0)
    pts_max = pts.max(axis=0)
    scale = np.maximum(pts_max - pts_min, 1e-5)
    offset = pts_min
    pts_norm = (pts - offset) / scale * 2.0 - 1.0
    return pts_norm, offset, scale

src_norm, src_off, src_scale = normalize_pts(mkpts_src_clean)
ref_norm, ref_off, ref_scale = normalize_pts(mkpts_ref_clean)

tps = cv2.createThinPlateSplineShapeTransformer()
tps.setRegularizationParameter(0.0)

matches = [cv2.DMatch(i, i, 0) for i in range(len(ref_norm))]
tps.estimateTransformation(
    ref_norm.reshape(1, -1, 2).astype(np.float32), 
    src_norm.reshape(1, -1, 2).astype(np.float32), 
    matches
)

retval, pred_src_norm = tps.applyTransformation(ref_norm.reshape(1, -1, 2).astype(np.float32))
print("retval:", retval)
if retval != 0:
    pred_src = ((pred_src_norm.reshape(-1, 2) + 1.0) / 2.0) * src_scale + src_off
    res = np.linalg.norm(mkpts_src_clean - pred_src, axis=1)
    print("RMSE forward (norm + dedup):", np.sqrt(np.mean(res**2)))
