import cv2
import numpy as np

canvas_w, canvas_h = 6000, 15000
np.random.seed(42)
p_can = np.random.rand(50, 2) * [canvas_w, canvas_h]
p_ref = p_can * [1400/6000, 3000/15000]

can_min, can_max = p_can.min(axis=0), p_can.max(axis=0)
can_scale = np.maximum(can_max - can_min, 1e-5)
can_norm = (p_can - can_min) / can_scale * 2.0 - 1.0

ref_min, ref_max = p_ref.min(axis=0), p_ref.max(axis=0)
ref_scale = np.maximum(ref_max - ref_min, 1e-5)
ref_norm = (p_ref - ref_min) / ref_scale * 2.0 - 1.0

tps = cv2.createThinPlateSplineShapeTransformer()
tps.setRegularizationParameter(0.0)
tps.estimateTransformation(
    can_norm.reshape(1, -1, 2).astype(np.float32), 
    ref_norm.reshape(1, -1, 2).astype(np.float32), 
    [cv2.DMatch(i, i, 0) for i in range(len(p_ref))]
)

# Test with 10 points
grid_pts = np.array([[[100.0, 100.0]]], dtype=np.float32)
grid_norm = (grid_pts - can_min) / can_scale * 2.0 - 1.0
retval, out = tps.applyTransformation(grid_norm)
print("1 pt retval:", retval, "out:", out)

# Test with 6000 points
X, Y = np.meshgrid(np.arange(6000), np.arange(1))
grid_pts = np.stack([X.ravel(), Y.ravel()], axis=-1).reshape(1, -1, 2).astype(np.float32)
grid_norm = (grid_pts - can_min) / can_scale * 2.0 - 1.0
retval, out = tps.applyTransformation(grid_norm)
print("6000 pts retval:", retval)
print("6000 pts out min/max:", np.nanmin(out), np.nanmax(out))
