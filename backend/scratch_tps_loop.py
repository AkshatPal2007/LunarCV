import cv2
import numpy as np

canvas_w, canvas_h = 6000, 15000
# Fake points
np.random.seed(42)
p_can = np.random.rand(50, 2) * [canvas_w, canvas_h]
p_ref = p_can * [1400/6000, 3000/15000]

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

y = 0
y_end = 100
X, Y = np.meshgrid(np.arange(canvas_w), np.arange(y, y_end))
grid_pts = np.stack([X.ravel(), Y.ravel()], axis=-1).reshape(1, -1, 2).astype(np.float32)

grid_norm = (grid_pts - can_min) / can_scale * 2.0 - 1.0
retval, ref_coords_norm = tps_inv.applyTransformation(grid_norm)
print("retval:", retval)
print("grid_norm sample:", grid_norm[0, :5])
print("ref_coords_norm sample:", ref_coords_norm[0, :5])

ref_coords = ((ref_coords_norm.reshape(-1, 2) + 1.0) / 2.0) * ref_scale + ref_min
print("ref_coords sample:", ref_coords[:5])
