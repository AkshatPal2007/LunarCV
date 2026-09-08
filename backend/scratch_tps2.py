import cv2
import numpy as np
import time

ref_img = np.ones((100, 100), dtype=np.uint8) * 255
pts_ref = np.array([[0,0], [100,0], [100,100], [0,100]], dtype=np.float32)
pts_src = np.array([[10,10], [200,10], [200,200], [10,200]], dtype=np.float32)
x_min, y_min = 0, 0
canvas_w, canvas_h = 250, 250

tps_inv = cv2.createThinPlateSplineShapeTransformer()
matches = [cv2.DMatch(i,i,0) for i in range(4)]
tps_inv.estimateTransformation(pts_src.reshape(1,-1,2), pts_ref.reshape(1,-1,2), matches)

t0 = time.time()
X, Y = np.meshgrid(np.arange(canvas_w), np.arange(canvas_h))
canvas_pts = np.stack([X.ravel(), Y.ravel()], axis=-1).reshape(1, -1, 2).astype(np.float32)
_, src_coords = tps_inv.applyTransformation(canvas_pts)
src_coords = src_coords.reshape(canvas_h, canvas_w, 2)
map_x = src_coords[:, :, 0].astype(np.float32)
map_y = src_coords[:, :, 1].astype(np.float32)

warped = cv2.remap(ref_img, map_x, map_y, cv2.INTER_LINEAR)
t1 = time.time()
print("Warped shape:", warped.shape, "Time:", t1-t0)
