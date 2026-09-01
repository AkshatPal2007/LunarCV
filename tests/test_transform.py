import numpy as np
import pytest
from transform import estimate_transform, transform_points

def test_transform_points():
    M = np.array([
        [2, 0, 10],
        [0, 2, 20],
        [0, 0, 1]
    ], dtype=np.float32)
    
    pts = np.array([
        [0, 0],
        [10, 10]
    ], dtype=np.float32)
    
    pred = transform_points(pts, M)
    
    assert np.allclose(pred[0], [10, 20])
    assert np.allclose(pred[1], [30, 40])


def test_estimate_transform_affine():
    # Src is a scaled and translated version of Ref
    pts_ref = np.array([
        [0, 0],
        [10, 0],
        [0, 10],
        [10, 10]
    ], dtype=np.float32)
    
    pts_src = np.array([
        [10, 20],
        [30, 20],
        [10, 40],
        [30, 40]
    ], dtype=np.float32)
    
    M, mask = estimate_transform(pts_src, pts_ref, model="affine")
    
    assert M is not None
    assert np.all(mask)
    
    # M maps Ref -> Src
    # M should be roughly [2, 0, 10; 0, 2, 20; 0, 0, 1]
    assert np.isclose(M[0, 0], 2.0)
    assert np.isclose(M[1, 1], 2.0)
    assert np.isclose(M[0, 2], 10.0)
    assert np.isclose(M[1, 2], 20.0)
