import cv2
import numpy as np

mkpts_src = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_src.npy')
mkpts_ref = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_ref.npy')

def normalize_pts(pts):
    pts_min = pts.min(axis=0)
    pts_max = pts.max(axis=0)
    scale = np.maximum(pts_max - pts_min, 1e-5)
    offset = pts_min
    pts_norm = (pts - offset) / scale * 2.0 - 1.0
    return pts_norm, offset, scale

src_norm, src_off, src_scale = normalize_pts(mkpts_src)
ref_norm, ref_off, ref_scale = normalize_pts(mkpts_ref)

tps = cv2.createThinPlateSplineShapeTransformer()
tps.setRegularizationParameter(0.0) # Exact interpolation

matches = [cv2.DMatch(i, i, 0) for i in range(len(ref_norm))]
tps.estimateTransformation(
    ref_norm.reshape(1, -1, 2).astype(np.float32), 
    src_norm.reshape(1, -1, 2).astype(np.float32), 
    matches
)

retval, pred_src_norm = tps.applyTransformation(ref_norm.reshape(1, -1, 2).astype(np.float32))
print("retval (0.0 reg):", retval)

if retval != 0:
    pred_src = ((pred_src_norm.reshape(-1, 2) + 1.0) / 2.0) * src_scale + src_off
    res = np.linalg.norm(mkpts_src - pred_src, axis=1)
    print("RMSE forward (reg 0.0):", np.sqrt(np.mean(res**2)))
else:
    print("Failed with 0.0 reg")

tps.setRegularizationParameter(0.0001)
tps.estimateTransformation(
    ref_norm.reshape(1, -1, 2).astype(np.float32), 
    src_norm.reshape(1, -1, 2).astype(np.float32), 
    matches
)
retval, pred_src_norm = tps.applyTransformation(ref_norm.reshape(1, -1, 2).astype(np.float32))
pred_src = ((pred_src_norm.reshape(-1, 2) + 1.0) / 2.0) * src_scale + src_off
res = np.linalg.norm(mkpts_src - pred_src, axis=1)
print("RMSE forward (reg 0.0001):", np.sqrt(np.mean(res**2)))

