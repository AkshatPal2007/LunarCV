import cv2
import numpy as np

mkpts_src_ref = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_src.npy')
mkpts_ref_ref = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_ref.npy')

pts_canvas = mkpts_src_ref.copy()
pts_ref = mkpts_ref_ref.copy()

tps_inv = cv2.createThinPlateSplineShapeTransformer()
matches = [cv2.DMatch(i, i, 0) for i in range(len(pts_ref))]
tps_inv.estimateTransformation(
    pts_canvas.reshape(1, -1, 2).astype(np.float32), 
    pts_ref.reshape(1, -1, 2).astype(np.float32), 
    matches
)

canvas_pts = np.array([[[1000, 1000]]], dtype=np.float32)
retval, src_coords = tps_inv.applyTransformation(canvas_pts)
print("retval:", retval)
print("canvas_pts:\n", canvas_pts)
print("src_coords:\n", src_coords)

# Test forward mapping to see if it failed too
tps = cv2.createThinPlateSplineShapeTransformer()
tps.estimateTransformation(
    pts_ref.reshape(1, -1, 2).astype(np.float32), 
    pts_canvas.reshape(1, -1, 2).astype(np.float32), 
    matches
)
retval2, pred_src = tps.applyTransformation(pts_ref.reshape(1, -1, 2).astype(np.float32))
print("retval2:", retval2)
res = np.linalg.norm(pts_canvas - pred_src.reshape(-1, 2), axis=1)
print("RMSE forward:", np.sqrt(np.mean(res**2)))

