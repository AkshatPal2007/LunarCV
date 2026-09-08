import cv2
import numpy as np

mkpts_src = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_src.npy')
mkpts_ref = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_ref.npy')

# Remove duplicates
keep_mask = np.ones(len(mkpts_ref), dtype=bool)
for i in range(len(mkpts_ref)):
    if not keep_mask[i]:
        continue
    d1 = np.linalg.norm(mkpts_src - mkpts_src[i], axis=1)
    d2 = np.linalg.norm(mkpts_ref - mkpts_ref[i], axis=1)
    close_idx = np.where((d1 < 5.0) | (d2 < 5.0))[0]
    for j in close_idx:
        if j != i:
            keep_mask[j] = False

mkpts_src_clean = mkpts_src[keep_mask]
mkpts_ref_clean = mkpts_ref[keep_mask]
print(f"Points after dedup: {len(mkpts_src_clean)} / {len(mkpts_src)}")

tps = cv2.createThinPlateSplineShapeTransformer()
matches = [cv2.DMatch(i, i, 0) for i in range(len(mkpts_ref_clean))]
tps.estimateTransformation(
    mkpts_ref_clean.reshape(1, -1, 2).astype(np.float32), 
    mkpts_src_clean.reshape(1, -1, 2).astype(np.float32), 
    matches
)

retval, pred_src = tps.applyTransformation(mkpts_ref_clean.reshape(1, -1, 2).astype(np.float32))
print("retval:", retval)
if retval != 0:
    res = np.linalg.norm(mkpts_src_clean - pred_src.reshape(-1, 2), axis=1)
    print("RMSE forward (raw):", np.sqrt(np.mean(res**2)))
