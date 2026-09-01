import numpy as np
import pytest
from evaluate import calculate_reprojection_errors, calculate_spatial_metrics

def test_calculate_reprojection_errors():
    # Identity transform
    M = np.eye(3)
    
    pts_src = np.array([[10, 10], [20, 20]], dtype=np.float32)
    # Ref is exactly matching src, so error should be 0
    pts_ref = np.array([[10, 10], [20, 20]], dtype=np.float32)
    
    metrics = calculate_reprojection_errors(pts_src, pts_ref, M)
    assert metrics["fwd_rmse"] == 0.0
    assert metrics["bwd_rmse"] == 0.0
    
    # Translation transform
    M = np.array([
        [1, 0, 5],
        [0, 1, 5],
        [0, 0, 1]
    ], dtype=np.float32)
    
    # M maps Ref -> Src. So if Ref is (10, 10), Src should be (15, 15) for 0 error.
    pts_src = np.array([[15, 15]], dtype=np.float32)
    pts_ref = np.array([[10, 10]], dtype=np.float32)
    
    metrics = calculate_reprojection_errors(pts_src, pts_ref, M)
    assert metrics["fwd_rmse"] == 0.0
    assert metrics["bwd_rmse"] == 0.0


def test_calculate_spatial_metrics():
    # Create a square of points in a 100x100 image
    # Grid size 2x2. Cells are 50x50.
    pts_src = np.array([
        [10, 10], # 0,0
        [10, 90], # 1,0
        [90, 10], # 0,1
        [90, 90]  # 1,1
    ])
    
    img_shape = (100, 100)
    
    metrics = calculate_spatial_metrics(pts_src, img_shape, grid_size=(2, 2))
    
    # Hull should be 80 * 80 = 6400
    # Total area is 10000
    # Coverage = 64.0%
    assert np.isclose(metrics["hull_coverage"], 64.0)
    
    # 4 points, one in each cell -> 100% occupancy
    assert metrics["grid_occupancy"] == 100.0
    assert metrics["occupied_cells"] == 4
