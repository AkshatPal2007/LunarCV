import cv2
import numpy as np

mkpts_src = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_src.npy')
mkpts_ref = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_ref.npy')

keep = np.ones(len(mkpts_ref), dtype=bool)
for i in range(len(mkpts_ref)):
    if not keep[i]: continue
    d_ref = np.linalg.norm(mkpts_ref - mkpts_ref[i], axis=1)
    d_can = np.linalg.norm(mkpts_src - mkpts_src[i], axis=1)
    close = np.where((d_ref < 2.0) | (d_can < 2.0))[0]
    for j in close:
        if j != i: keep[j] = False

p_ref = mkpts_ref[keep]
p_can = mkpts_src[keep]

can_min, can_max = p_can.min(axis=0), p_can.max(axis=0)
can_scale = np.maximum(can_max - can_min, 1e-5)
can_norm = (p_can - can_min) / can_scale * 2.0 - 1.0

ref_min, ref_max = p_ref.min(axis=0), p_ref.max(axis=0)
ref_scale = np.maximum(ref_max - ref_min, 1e-5)
ref_norm = (p_ref - ref_min) / ref_scale * 2.0 - 1.0

tps_inv = cv2.createThinPlateSplineShapeTransformer()
tps_inv.setRegularizationParameter(0.0)
tps_inv.estimateTransformation(
    can_norm.reshape(1, -1, 2).astype(np.float32), 
    ref_norm.reshape(1, -1, 2).astype(np.float32), 
    [cv2.DMatch(i, i, 0) for i in range(len(p_ref))]
)

# Test applyTransformation on chunk size 6000
canvas_w = 6000
y = 0
y_end = 1
X, Y = np.meshgrid(np.arange(canvas_w), np.arange(y, y_end))
grid_pts = np.stack([X.ravel(), Y.ravel()], axis=-1).reshape(1, -1, 2).astype(np.float32)

grid_norm = (grid_pts - can_min) / can_scale * 2.0 - 1.0
retval, ref_coords_norm = tps_inv.applyTransformation(grid_norm)

print("retval:", retval)
print("Out shape:", ref_coords_norm.shape)
print("Max abs value:", np.nanmax(np.abs(ref_coords_norm)))

