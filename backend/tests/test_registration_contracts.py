"""Synthetic arrays below test numerical logic only, never lunar performance."""

import json
from unittest.mock import Mock

import cv2
import numpy as np
import pytest
import torch

from lunarcv.engine import RegistrationConfig, fit_transform
from lunarcv.evaluation.controls import evaluate_controls
from lunarcv.evaluation.metrics import RegistrationMetrics, quality_gate
from lunarcv.io.products import read_product
from lunarcv.io.raster import parse_pds4_xml
from lunarcv.matching.cache import load_matches, save_matches
from lunarcv.matching.ensemble import EnsembleMatcher
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.registration.coordinates import PixelFrame, project_points
from lunarcv.registration.subpixel import refine_matches


def test_crop_resize_native_roundtrip_and_pixel_centers():
    frame = PixelFrame((800, 82500), (6.0, 4.0))
    points = np.array([[0.0, 0.0], [10.25, 20.75]])
    native = project_points(frame.to_native, points)
    assert np.allclose(native[0], [802.5, 82501.5])
    assert np.allclose(project_points(np.linalg.inv(frame.to_native), native), points)


def test_exact_affine_mapping_and_collinear_rejection():
    points = np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0], [10.0, 10.0]])
    matrix = np.array([[1.1, 0.2, 5.0], [-0.1, 0.9, -2.0], [0.0, 0.0, 1.0]])
    assert np.allclose(
        fit_transform(points, project_points(matrix, points), "affine"), matrix
    )
    with pytest.raises(ValueError, match="collinear"):
        fit_transform(
            np.array([[0, 0], [1, 1], [2, 2]]),
            np.array([[1, 1], [2, 2], [3, 3]]),
            "affine",
        )


def test_numeric_cache_preserves_arrays_and_rejects_stale_or_corrupt(tmp_path):
    path = tmp_path / "matches.npz"
    points = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    save_matches(
        path, {"input": "hash"}, points, points + 2, np.array([0.2, 0.8]), {"count": 2}
    )
    result = load_matches(path, {"input": "hash"})
    assert np.array_equal(result[0], points)
    assert np.allclose(result[2], [0.2, 0.8])
    assert load_matches(path, {"input": "changed"}) is None
    path.write_bytes(b"broken cache")
    assert load_matches(path, {"input": "hash"}) is None


def test_lightglue_scores_and_explicit_extractor_resolution():
    matcher = LightGlueFeatureMatcher.__new__(LightGlueFeatureMatcher)
    matcher.device = torch.device("cpu")
    matcher.max_dim = 1024
    extractor = Mock()
    extractor.extract.return_value = {
        "keypoints": torch.tensor([[[10.0, 10.0], [20.0, 20.0]]])
    }
    matcher.extractor = extractor
    matcher.matcher = Mock(
        return_value={
            "matches": torch.tensor([[[0, 0], [1, 1]]]),
            "scores": [torch.tensor([0.15, 0.95])],
        }
    )
    image = np.zeros((128, 128), np.uint8)
    _, _, scores = matcher.match(image, image)
    assert np.allclose(scores, [0.15, 0.95])
    assert all(
        call.kwargs == {"resize": None} for call in extractor.extract.call_args_list
    )


def test_ensemble_requires_agreement_at_both_endpoints():
    src = np.array([[10.0, 10.0], [40.0, 40.0]], np.float32)
    first = Mock()
    first.match.return_value = (src, src, np.array([0.2, 0.9], np.float32))
    second = Mock()
    second.match.return_value = (
        src + 0.1,
        np.array([[10.1, 10.1], [100.0, 100.0]]),
        np.ones(2),
    )
    ensemble = EnsembleMatcher([first, second])
    a, b, scores = ensemble.match(
        np.zeros((64, 64), np.uint8), np.zeros((64, 64), np.uint8)
    )
    assert np.allclose(scores, [1.2, 0.9])
    assert ensemble.diagnostics["agreed_matches"] == 1
    assert np.array_equal(a, src)
    assert np.array_equal(b, src)


def test_fractional_identity_refinement_keeps_pair_aligned():
    image = np.random.default_rng(7).integers(0, 255, (128, 128), dtype=np.uint8)
    points = np.array([[40.25, 60.35], [70.4, 50.1]], np.float32)
    src, ref, stats = refine_matches(image, image, points, points)
    assert np.allclose(src, ref, atol=1e-4)
    assert stats["successfully_refined"] == 2


def test_refinement_rejects_flat_texture():
    image = np.full((64, 64), 100, np.uint8)
    points = np.array([[32.25, 32.25]], np.float32)
    src, _, stats = refine_matches(image, image, points, points)
    assert np.array_equal(src, points)
    assert stats["successfully_refined"] == 0


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_quality_gate_rejects_nonfinite_accuracy(value):
    metrics = RegistrationMetrics(
        20, 12, 0.6, 1.0, 1.0, 1.0, 50.0, 1.0, "", value, 1.0, "heldout_valid"
    )
    assert quality_gate(metrics).startswith("REJECT")


def test_window_masks_keep_zero_valid_and_original_dtype(tmp_path):
    path = tmp_path / "native.tif"
    image = np.arange(10000, dtype=np.uint16).reshape(100, 100)
    assert cv2.imwrite(str(path), image)
    product = read_product(path, (0, 0, 50, 50))
    assert product.data.dtype == np.uint16
    assert product.valid[0, 0]
    assert product.data[0, 0] == 0
    assert product.original_shape == (100, 100)
    with pytest.raises(ValueError, match="max_pixels"):
        read_product(path, max_pixels=100)


def test_pds4_signed_little_endian_from_declared_type(tmp_path):
    path = tmp_path / "test.img"
    path.with_suffix(".xml").write_text(
        """<Product><Array_2D_Image><offset>0</offset><data_type>SignedLSB2</data_type><Axis_Array><axis_name>Line</axis_name><elements>2</elements></Axis_Array><Axis_Array><axis_name>Sample</axis_name><elements>2</elements></Axis_Array></Array_2D_Image></Product>"""
    )
    meta = parse_pds4_xml(path)
    assert meta["dtype"] == np.dtype("<i2")


def test_external_controls_cannot_reuse_fit_features(tmp_path):
    points = np.array([[i * 10.0, i * 5.0] for i in range(6)])
    payload = {
        "coordinate_frame": "native_pixels",
        "independent_of_matching": True,
        "method": "unit test fixture only",
        "provenance": "unit test",
        "uncertainty_reference_px": 0.2,
        "points": [{"source": p.tolist(), "reference": p.tolist()} for p in points],
    }
    path = tmp_path / "controls.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="overlap"):
        evaluate_controls(path, np.eye(3), points, points)


def test_registration_config_rejects_invalid_matchers_and_memory_limits():
    with pytest.raises(ValueError, match="matcher"):
        RegistrationConfig(matcher="loftr")
    with pytest.raises(ValueError, match="max_pixels"):
        RegistrationConfig(max_pixels=100_000_000)


def test_secondary_empty_fallback_resets_for_new_scene():
    source = np.array([[10.0, 10.0], [20.0, 20.0]], np.float32)
    primary = Mock()
    primary.match.return_value = (source, source, np.array([0.4, 0.8]))
    secondary = Mock()
    secondary.match.return_value = (np.empty((0, 2)), np.empty((0, 2)), np.empty(0))
    ensemble = EnsembleMatcher([primary, secondary])
    image = np.zeros((64, 64), np.uint8)
    ensemble.match(image, image)
    ensemble.match(image, image)
    assert secondary.match.call_count == 1
    ensemble.reset_run()
    ensemble.match(image, image)
    assert secondary.match.call_count == 2


def test_rift_patch_conversion_preserves_values():
    # Unit logic only. These arrays are never evaluation/demo imagery.
    from lunarcv.matching.rift2_matcher import RIFT2

    model = RIFT2(n_jobs=1)
    image = np.random.default_rng(41).integers(0, 6, size=(117, 139))
    for angle in (0, 17.5, 90, 213):
        old = model.extract_patches(image, 71.25, 52.75, 48, angle)
        optimized = model.extract_patches(
            image.astype(np.float32), 71.25, 52.75, 48, angle
        )
        np.testing.assert_array_equal(old, optimized)


def test_rift_vector_histograms_exactly_match_original_cells():
    from lunarcv.matching.rift2_matcher import RIFT2

    rng = np.random.default_rng(73)
    for shape in ((97, 97), (96, 101), (13, 15)):
        patch = rng.uniform(-2, 9, shape)
        patch.flat[:8] = [0, 1, 2, 3, 4, 5, 6, 7]
        original = np.zeros((6, 6, 6))
        ys, xs = shape
        for j in range(6):
            for i in range(6):
                clip = patch[
                    round(j * ys / 6) : round((j + 1) * ys / 6),
                    round(i * xs / 6) : round((i + 1) * xs / 6),
                ]
                original[j, i] = np.histogram(clip, bins=np.arange(1, 8))[0]
        np.testing.assert_array_equal(
            RIFT2.cell_histograms(patch, 6, 6), original.flatten()
        )


def test_legacy_loader_requires_explicit_crop_and_preserves_origin(tmp_path):
    import cv2

    from app.services.image_loader import ImageLoadError, load_image_auto

    path = tmp_path / "unit.png"
    cv2.imwrite(str(path), np.arange(128 * 128, dtype=np.uint8).reshape(128, 128))
    with pytest.raises(ImageLoadError, match="explicit crop"):
        load_image_auto(path, max_dimension=64)
    image, metadata = load_image_auto(path, max_dimension=64, bounds=(20, 30, 84, 94))
    assert image.shape == (64, 64)
    assert tuple(metadata["original_shape"]) == (128, 128)
    assert tuple(metadata["bounds_xyxy_exclusive"]) == (20, 30, 84, 94)
