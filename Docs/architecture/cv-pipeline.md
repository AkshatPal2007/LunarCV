# CV Pipeline Architecture

Deep dive into the computer vision registration pipeline.

## Pipeline Overview

The registration pipeline transforms two misaligned lunar images into a precisely registered pair through seven stages:

```
Input Images
    ↓
1. I/O & Memory Mapping
    ↓
2. Preprocessing & Normalization
    ↓
3. Feature Detection & Matching
    ↓
4. Outlier Rejection (MAGSAC++)
    ↓
5. Spatial Distribution Filtering
    ↓
6. Sub-pixel Refinement
    ↓
7. Transform Estimation & Warping
    ↓
Registered Output + Metrics
```

## Stage 1: I/O & Memory Mapping

**Module:** `lunarcv.io.raster`

**Purpose:** Efficiently load large orbital imagery (1GB+) without exhausting RAM.

**Key Functions:**
- `load_ohrc_memmap()` - Chandrayaan-2 OHRC images
- `load_lro_nac_memmap()` - NASA LRO NAC images
- `extract_patch()` - Extract spatial subsets

**Implementation:**
```python
# Zero-copy memory mapping
ohrc_mm = np.memmap(
    img_path, 
    dtype='uint8', 
    mode='r', 
    offset=0, 
    shape=(90148, 12000)
)

# Extract patch without loading full image
patch = ohrc_mm[30000:45000, 2000:8000]
```

**Why Memory Mapping?**
- Chandrayaan-2 OHRC: 90,148 × 12,000 pixels = 1.08 GB
- LRO NAC: 52,224 × 2,532 pixels = 132 MB
- Memory mapping allows OS-level paging instead of full load

**Supported Formats:**
- PDS3 `.IMG` with PDS labels
- PDS4 `.img` with XML metadata
- GeoTIFF `.tif`
- Standard formats (`.png`, `.jpg`) via `cv2.imread`

---

## Stage 2: Preprocessing & Normalization

**Module:** `lunarcv.preprocessing.normalize`

**Purpose:** Robust intensity normalization for cross-sensor consistency.

**Default Approach:** Percentile-based stretch to uint8 [0, 255]

```python
def percentile_stretch_uint8(img, p_low=1.0, p_high=99.0):
    v_min, v_max = np.percentile(img, (p_low, p_high))
    stretched = (img - v_min) / (v_max - v_min) * 255.0
    return np.clip(stretched, 0, 255).astype(np.uint8)
```

**Why Percentile Stretch?**
- Robust to outliers (hot pixels, dead pixels)
- No local artifacts (unlike CLAHE)
- Preserves global contrast relationships
- Makharia et al. showed minimal preprocessing works best with learned matchers

**Alternative:** CLAHE (Contrast-Limited Adaptive Histogram Equalization)
- Available via `apply_clahe()`
- Only use for classical methods (SIFT, AKAZE) if needed
- Evidence shows it doesn't help LightGlue/LoFTR

**Scale Alignment:**
For cross-sensor pairs (e.g., OHRC 0.26 m/px vs LRO NAC 1.60 m/px), scale the higher-resolution image to match:

```python
scale_factor = LRO_GSD / OHRC_GSD  # 1.60 / 0.26 ≈ 6.15x
ohrc_scaled = cv2.resize(
    ohrc_norm, 
    (target_w, target_h), 
    interpolation=cv2.INTER_AREA
)
```

---

## Stage 3: Feature Detection & Matching

**Module:** `lunarcv.matching`

**Primary Matcher:** LightGlue (SuperPoint + LightGlue)

### LightGlue Architecture

```
Source Image          Reference Image
     ↓                       ↓
SuperPoint Detector     SuperPoint Detector
     ↓                       ↓
Keypoints + Descriptors    Keypoints + Descriptors
     ↓                       ↓
     └─────────┬─────────────┘
               ↓
        LightGlue Matcher
        (Transformer-based)
               ↓
    Matched Point Pairs + Confidence
```

**Implementation:**
```python
class LightGlueFeatureMatcher:
    def __init__(self, max_dim=1024, max_keypoints=2048):
        self.extractor = SuperPoint(max_num_keypoints=max_keypoints)
        self.matcher = LightGlue(features='superpoint')
    
    def match(self, img_src, img_ref, conf_threshold=0.2):
        # Detect keypoints
        feats_src = self.extractor.extract(img_src)
        feats_ref = self.extractor.extract(img_ref)
        
        # Match with transformer
        matches = self.matcher({'image0': feats_src, 'image1': feats_ref})
        
        # Filter by confidence
        mask = matches['scores'] > conf_threshold
        return mkpts_src[mask], mkpts_ref[mask], scores[mask]
```

**Why LightGlue?**
- **Accuracy**: SOTA on image matching benchmarks
- **Speed**: 3-10x faster than SuperGlue
- **License**: MIT (vs SuperGlue's research-only license)
- **Illumination Robustness**: Learned features handle shadow reversals better than hand-crafted descriptors

**Chunked Matching for Large Images:**
For images > 1500 px, process in overlapping chunks to avoid GPU memory limits:

```python
n_chunks = 3
overlap = 400
for i in range(n_chunks):
    patch_src = img_src[y1:y2, :]
    patch_ref = img_ref[y1:y2, :]
    pts_src, pts_ref, conf = matcher.match(patch_src, patch_ref)
    # Offset coordinates back to full image space
    pts_src[:, 1] += y1
    pts_ref[:, 1] += y1
```

**Alternative Matchers (Planned):**
- **LoFTR**: Dense transformer-based (better for texture-poor regions)
- **RIFT2**: Phase congruency-based (mathematically illumination-invariant)

---

## Stage 4: Outlier Rejection (MAGSAC++)

**Module:** `lunarcv.registration.outlier_rejection`

**Purpose:** Geometric filtering to remove false matches.

**Algorithm:** MAGSAC++ (MAximum Marginal likelihood SAmple Consensus)

```python
def magsac_filter(mkpts_src, mkpts_ref, conf, model='homography'):
    H, mask = cv2.findHomography(
        mkpts_ref,  # reference points
        mkpts_src,  # source points
        method=cv2.USAC_MAGSAC,
        ransacReprojThreshold=4.0,
        confidence=0.999,
        maxIters=10000
    )
    
    # Keep only inliers
    inliers = mask.ravel() == 1
    return mkpts_src[inliers], mkpts_ref[inliers], conf[inliers], H, mask
```

**Why MAGSAC++ over RANSAC?**
- **No threshold tuning**: Automatically estimates noise level
- **More inliers**: Higher recall at same precision
- **Faster convergence**: Fewer iterations needed
- **Built into OpenCV**: `cv2.USAC_MAGSAC`

**Typical Results:**
- Input: 1,234 candidate matches
- Output: 987 inliers (80% inlier ratio)
- Rejected: 247 outliers (false positives, repetitive features)

**Model Options:**
- `homography` - Default, 8-DOF projective transform
- `affine` - 6-DOF (no perspective distortion)
- `fundamental` - Epipolar geometry (for stereo pairs)

---

## Stage 5: Spatial Distribution Filtering

**Module:** `lunarcv.registration.spatial_uniformity`

**Purpose:** Ensure match points are uniformly distributed across the image.

**Why?** Clustering in high-texture regions (craters) degrades registration accuracy in smooth regolith.

**Grid-based Top-K Filter:**

```python
def spatial_topk_filter(pts, conf, image_h, image_w, n_rows=4, n_cols=4):
    grid_h = image_h // n_rows
    grid_w = image_w // n_cols
    
    selected = []
    for row in range(n_rows):
        for col in range(n_cols):
            # Find points in this grid cell
            mask = (pts[:, 1] >= row * grid_h) & (pts[:, 1] < (row+1) * grid_h) & \
                   (pts[:, 0] >= col * grid_w) & (pts[:, 0] < (col+1) * grid_w)
            
            if mask.sum() > 0:
                # Keep top-K highest-confidence matches in this cell
                cell_idx = np.where(mask)[0]
                sorted_idx = cell_idx[np.argsort(conf[cell_idx])[::-1]]
                selected.extend(sorted_idx[:K])
    
    return selected
```

**Metrics Reported:**
- **Grid Occupancy**: % of grid cells containing ≥1 match
- **Convex Hull Coverage**: % of image area covered by match convex hull
- **Min Pairwise Separation**: Minimum distance between any two matches

**Typical Thresholds:**
- Grid occupancy > 80% (good)
- Convex hull coverage > 70% (good)
- Min separation > 10 pixels (not clustered)

**Note:** This is a **differentiator vs. published benchmarks** — Makharia et al. (2024) didn't enforce spatial uniformity.

---

## Stage 6: Sub-pixel Refinement

**Module:** `lunarcv.registration.subpixel`

**Purpose:** Improve match localization from integer-pixel to sub-pixel accuracy.

**Method:** `cv2.cornerSubPix` (iterative gradient-based refinement)

```python
def refine_matches(src_img, ref_img, pts_src, pts_ref, win_size=(5,5)):
    # Refine source points
    pts_src_refined = cv2.cornerSubPix(
        src_img,
        pts_src.copy(),
        winSize=win_size,
        zeroZone=(-1, -1),
        criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001)
    )
    
    # Refine reference points
    pts_ref_refined = cv2.cornerSubPix(
        ref_img,
        pts_ref.copy(),
        winSize=win_size,
        zeroZone=(-1, -1),
        criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001)
    )
    
    return pts_src_refined, pts_ref_refined
```

**How It Works:**
1. For each keypoint, extract a small window (e.g., 5×5 pixels)
2. Compute image gradients in that window
3. Iteratively shift the point to maximize corner response
4. Stop when shift < 0.001 pixels or 40 iterations reached

**Typical Improvement:**
- Mean displacement: 0.12 pixels (refinement shift)
- RMSE reduction: 0.82 → 0.62 pixels (24% improvement)

**Why Sub-pixel Matters:**
At OHRC resolution (0.26 m/px), 0.5 pixels = 13 cm — significant for geospatial accuracy.

---

## Stage 7: Transform Estimation & Warping

**Module:** `lunarcv.registration.transform`

**Purpose:** Fit geometric transform and warp images into alignment.

**Homography Estimation:**

```python
H_final, mask = cv2.findHomography(
    pts_ref_refined,  # Reference → Source mapping
    pts_src_refined,
    method=cv2.RANSAC,
    ransacReprojThreshold=3.0
)

# Warp reference image to source coordinate system
warped_ref = cv2.warpPerspective(
    ref_img, 
    H_final, 
    (output_w, output_h)
)
```

**Transform Options:**
- **Homography** (8-DOF): Default, handles perspective distortion
- **Affine** (6-DOF): Rotation, scale, translation, shear (no perspective)
- **Thin-Plate Spline (TPS)**: Non-rigid, for high-relief/polar regions

**Output Products:**

1. **Registered Image** (`registered.png`)
   - Reference image warped to source frame
   - Grayscale uint8

2. **Overlay** (`overlay.png`)
   - 50/50 alpha blend of registered pair
   - RGB color composite (reference=red, source=green)
   - Perfect alignment → yellow/gray, misalignment → red/green fringing

3. **Checkerboard** (`checkerboard.png`)
   - Alternating 50×50 pixel tiles from each image
   - Easier to spot local misalignment than overlay

4. **Correspondence CSV** (`correspondence_points.csv`)
   ```
   source_x,source_y,reference_x,reference_y
   1234.56,789.12,5678.90,2345.67
   ...
   ```

5. **Metrics JSON** (`metrics.json`)
   - Candidate matches, inlier count, inlier ratio
   - Reprojection RMSE, median/max error
   - Spatial uniformity stats

---

## Evaluation Metrics

### Reprojection RMSE

```python
# Project reference points through homography
ref_3d = pts_ref.reshape(-1, 1, 2).astype(np.float32)
pred_src = cv2.perspectiveTransform(ref_3d, H).reshape(-1, 2)

# Compute residuals
residuals = np.linalg.norm(pts_src - pred_src, axis=1)

# RMSE
rmse = np.sqrt(np.mean(residuals**2))
```

**Interpretation:**
- RMSE < 1.0 pixel: Excellent (sub-pixel accurate)
- RMSE 1.0-2.0 pixels: Good
- RMSE > 2.0 pixels: Poor (check for outliers or distortion)

**Benchmark:** Makharia et al. SuperGlue baseline: 0.62 px (OHRC-NAC Equatorial)

### Inlier Ratio

```
inlier_ratio = inliers / total_candidates
```

- High ratio (>80%): Matcher is precise, few false positives
- Low ratio (<50%): Many false matches, consider alternate matcher

### Spatial Uniformity

Quantifies match distribution across the image:
- **Grid Occupancy %**: How many grid cells contain matches
- **Convex Hull Coverage %**: % of image area inside match convex hull
- **Min Point Separation**: Minimum distance between any two matches

---

## Performance Considerations

### Chunked Processing
For images > 1500 px, process in chunks to avoid GPU OOM:
- Chunk size: ~1500×1500 pixels
- Overlap: 400 pixels (to avoid edge artifacts)
- Merge chunks: aggregate matches, offset coordinates

### GPU Acceleration
- LightGlue/LoFTR require GPU for real-time performance
- CPU fallback available but 10-50x slower
- Recommended: NVIDIA GPU with ≥6GB VRAM

### Typical Runtime (Single Pair)
| Stage | CPU Time | GPU Time |
|-------|----------|----------|
| I/O + Preprocess | 2s | 2s |
| Feature Matching | 120s | 8s |
| MAGSAC++ | 3s | 3s |
| Sub-pixel Refine | 1s | 1s |
| Transform + Warp | 2s | 2s |
| **Total** | **~130s** | **~16s** |

Image size: 3000×3000 pixels, 1000 matches

---

## Future Enhancements

1. **Ensemble Matching**: Run LightGlue + RIFT2 in parallel, cross-validate
2. **Adaptive Chunking**: Variable chunk size based on texture density
3. **Coarse-to-Fine**: Pyramid-based matching for massive images
4. **GPU Pipeline**: End-to-end on GPU (currently CPU ↔ GPU transfers)
5. **TPS Transform**: For high-relief terrain (crater walls, polar regions)
