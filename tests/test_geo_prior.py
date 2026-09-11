from geo_prior import compute_overlap, estimate_scale_ratio, generate_tiles
from metadata import BoundingBox, ImageMetadata


def test_compute_overlap():
    src_meta = ImageMetadata("OHRC", 100, 100, 0.25, BoundingBox(0.0, 0.0, 10.0, 10.0))
    ref_meta = ImageMetadata("LRO", 100, 100, 1.0, BoundingBox(5.0, 5.0, 15.0, 15.0))
    overlap = compute_overlap(src_meta, ref_meta)
    assert overlap is not None
    assert overlap.min_lon == 5.0


def test_estimate_scale_ratio():
    src_meta = ImageMetadata("OHRC", 100, 100, 0.25, None)
    ref_meta = ImageMetadata("LRO", 100, 100, 1.0, None)
    ratio = estimate_scale_ratio(src_meta, ref_meta)
    assert ratio == 4.0


def test_generate_tiles():
    # 1000x1000 image, 512x512 tiles, 0 overlap
    tiles = generate_tiles(1000, 1000, 512, 0)
    assert len(tiles) == 4

    # Check bounds
    t1, t2, t3, t4 = tiles
    assert t1.x == 0 and t1.y == 0 and t1.width == 512 and t1.height == 512
    assert t2.x == 512 and t2.y == 0 and t2.width == 488 and t2.height == 512
    assert t3.x == 0 and t3.y == 512 and t3.width == 512 and t3.height == 488
    assert t4.x == 512 and t4.y == 512 and t4.width == 488 and t4.height == 488


def test_generate_tiles_overlap():
    tiles = generate_tiles(1000, 1000, 500, 100)  # stride 400
    # X: 0, 400, 800
    # Y: 0, 400, 800
    # total 3x3 = 9 tiles
    assert len(tiles) == 9
