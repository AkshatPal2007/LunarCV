import numpy as np
import pytest
from spatial_uniformity import filter_spatial_uniformity

def test_filter_spatial_uniformity_basic():
    # 4 points, each in a different 2x2 grid cell
    pts_src = np.array([
        [10, 10],   # cell 0,0
        [60, 10],   # cell 0,1
        [10, 60],   # cell 1,0
        [60, 60]    # cell 1,1
    ])
    pts_ref = pts_src + 5
    conf = np.array([0.9, 0.8, 0.7, 0.6])
    
    img_shape = (100, 100)
    
    f_src, f_ref, f_conf, keep_idx = filter_spatial_uniformity(
        pts_src, pts_ref, conf, img_shape, grid_size=(2, 2), top_k_per_cell=1, min_conf=0.0
    )
    
    assert len(f_src) == 4
    assert np.all(keep_idx == [0, 1, 2, 3])


def test_filter_spatial_uniformity_top_k():
    # 3 points in cell 0,0. We want top_k=2.
    pts_src = np.array([
        [10, 10],
        [15, 15],
        [20, 20]
    ])
    pts_ref = pts_src.copy()
    conf = np.array([0.1, 0.9, 0.5]) # indices 1 and 2 should be kept, index 0 dropped
    
    img_shape = (100, 100)
    
    f_src, f_ref, f_conf, keep_idx = filter_spatial_uniformity(
        pts_src, pts_ref, conf, img_shape, grid_size=(2, 2), top_k_per_cell=2, min_conf=0.0
    )
    
    assert len(f_src) == 2
    assert list(keep_idx) == [1, 2]
    
    
def test_filter_spatial_uniformity_min_conf():
    pts_src = np.array([[10, 10], [60, 60]])
    pts_ref = pts_src.copy()
    conf = np.array([0.1, 0.8])
    
    img_shape = (100, 100)
    
    f_src, _, _, keep_idx = filter_spatial_uniformity(
        pts_src, pts_ref, conf, img_shape, grid_size=(2, 2), min_conf=0.5
    )
    
    assert len(f_src) == 1
    assert keep_idx[0] == 1
