import numpy as np
import time
from scipy.interpolate import RBFInterpolator

mkpts_src = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_src.npy')
mkpts_ref = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_ref.npy')

# Remove duplicates
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

# Fit TPS using SciPy (Thin Plate Spline is kernel 'thin_plate_spline' with degree 1)
# RBFInterpolator(y, d, neighbors=None, smoothing=0.0, kernel='thin_plate_spline', epsilon=None, degree=1)
t0 = time.time()
rbf = RBFInterpolator(p_can, p_ref, kernel='thin_plate_spline', smoothing=0.0, degree=1)

# Evaluate on grid
canvas_w, canvas_h = 6000, 15000
y = 0
y_end = 1000
X, Y = np.meshgrid(np.arange(canvas_w), np.arange(y, y_end))
grid_pts = np.stack([X.ravel(), Y.ravel()], axis=-1)

pred = rbf(grid_pts)
t1 = time.time()

print("Time for 1000 rows:", t1 - t0)
print("Out shape:", pred.shape)
print("Sample out:", pred[:5])

