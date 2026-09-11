from metadata import BoundingBox, ImageMetadata


def test_bounding_box_intersection():
    bb1 = BoundingBox(0.0, 0.0, 10.0, 10.0)
    bb2 = BoundingBox(5.0, 5.0, 15.0, 15.0)
    intersection = bb1.intersection(bb2)

    assert intersection is not None
    assert intersection.min_lon == 5.0
    assert intersection.min_lat == 5.0
    assert intersection.max_lon == 10.0
    assert intersection.max_lat == 10.0


def test_bounding_box_no_intersection():
    bb1 = BoundingBox(0.0, 0.0, 5.0, 5.0)
    bb2 = BoundingBox(6.0, 6.0, 10.0, 10.0)
    intersection = bb1.intersection(bb2)
    assert intersection is None


def test_image_metadata_creation():
    data = {
        "sensor": "OHRC",
        "width": 1000,
        "height": 2000,
        "gsd_meters": 0.25,
        "bbox": {"min_lon": 0.0, "min_lat": 0.0, "max_lon": 1.0, "max_lat": 1.0},
    }
    meta = ImageMetadata.from_dict(data)
    assert meta.sensor == "OHRC"
    assert meta.width == 1000
    assert meta.gsd_meters == 0.25
    assert meta.bbox is not None
    assert meta.bbox.max_lat == 1.0
