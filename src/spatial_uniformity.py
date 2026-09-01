"""
spatial_uniformity.py — Spatial filtering and distribution logic for LunarCV.

Ensures that matches are not just densely packed into ambiguous micro-clusters
(e.g., repeating crater patterns), but instead are distributed globally across
the image footprint.
"""

import numpy as np

def filter_spatial_uniformity(
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    conf: np.ndarray,
    image_shape: tuple[int, int],
    grid_size: tuple[int, int] = (4, 4),
    top_k_per_cell: int = 5,
    min_conf: float = 0.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Filter matches to retain only the top-K highest confidence matches
    per grid cell in the source image space.
    
    Parameters
    ----------
    pts_src : ndarray (N, 2)
        Source image keypoints (x, y).
    pts_ref : ndarray (N, 2)
        Reference image keypoints (x, y).
    conf : ndarray (N,)
        Confidence scores for each match.
    image_shape : tuple (H, W)
        Shape of the source image used to define the spatial grid bounds.
    grid_size : tuple (Rows, Cols)
        Number of grid divisions (e.g., (4, 4) for 16 cells).
    top_k_per_cell : int
        Maximum number of matches to retain in each cell.
    min_conf : float
        Absolute minimum confidence to consider before spatial filtering.
        
    Returns
    -------
    filtered_src : ndarray (M, 2)
    filtered_ref : ndarray (M, 2)
    filtered_conf : ndarray (M,)
    keep_indices : ndarray (M,)
        The original indices of the retained points.
    """
    if len(pts_src) == 0:
        return pts_src, pts_ref, conf, np.array([], dtype=int)
        
    h, w = image_shape
    grid_rows, grid_cols = grid_size
    
    # Pre-filter by absolute confidence floor if requested
    valid_mask = conf >= min_conf
    if not np.any(valid_mask):
        empty = np.empty((0, 2), dtype=np.float32)
        return empty, empty, np.empty((0,), dtype=np.float32), np.array([], dtype=int)

    # Determine cell dimensions
    cell_h = h / grid_rows
    cell_w = w / grid_cols
    
    # Create a dictionary to hold indices for each cell
    grid_cells = {}
    
    # Assign each point to a grid cell based on its source (x, y) coordinates
    for i in range(len(pts_src)):
        if not valid_mask[i]:
            continue
            
        x, y = pts_src[i]
        
        # Calculate row and col indices, bounded to max grid size
        r = min(int(y / cell_h), grid_rows - 1)
        c = min(int(x / cell_w), grid_cols - 1)
        
        # Handle points that might be slightly outside bounds (e.g., x < 0)
        r = max(0, r)
        c = max(0, c)
        
        cell_id = (r, c)
        if cell_id not in grid_cells:
            grid_cells[cell_id] = []
        grid_cells[cell_id].append(i)
        
    keep_indices = []
    
    # Process each cell: sort by confidence (descending) and take top K
    for cell_id, indices in grid_cells.items():
        # Sort indices by confidence
        sorted_indices = sorted(indices, key=lambda i: conf[i], reverse=True)
        # Retain only top K
        keep_indices.extend(sorted_indices[:top_k_per_cell])
        
    # Convert to numpy array and ensure deterministic ordering (e.g., sorted by index)
    keep_indices = np.array(sorted(keep_indices), dtype=int)
    
    return pts_src[keep_indices], pts_ref[keep_indices], conf[keep_indices], keep_indices
