import numpy as np

mkpts_ref = np.load('/home/akshat/Projects/LunarCV/data/processed/matches/ohrc_lro_mkpts_ref.npy')
print("Unique ref points:", len(np.unique(mkpts_ref, axis=0)))
print("Total ref points:", len(mkpts_ref))

# Find the distance between all pairs
from scipy.spatial.distance import pdist
dist = pdist(mkpts_ref)
print("Min distance between ref points:", np.min(dist))
