"""Tests for src/blur_laplacian.py."""

import sys
import os

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from blur_laplacian import (
    compute_blur_score_laplacian,
    blur_label_and_color,
    normalize_score,
)


def _make_sharp_bgr(size: int = 64) -> np.ndarray:
    """Synthesise a BGR image with a sharp high-contrast edge."""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:, size // 2 :, :] = 255  # hard black/white boundary
    return img


def _make_blurry_bgr(size: int = 64, sigma: float = 8.0) -> np.ndarray:
    """Synthesise a BGR image that has been heavily Gaussian-blurred."""
    sharp = _make_sharp_bgr(size)
    return cv2.GaussianBlur(sharp, (0, 0), sigma)


class TestComputeBlurScoreLaplacian:
    """Tests for compute_blur_score_laplacian."""

    def test_sharp_image_higher_score_than_blurry(self):
        """Sharp images must receive a higher score than blurry ones."""
        sharp = _make_sharp_bgr()
        blurry = _make_blurry_bgr()

        sharp_score = compute_blur_score_laplacian(sharp)
        blurry_score = compute_blur_score_laplacian(blurry)

        assert sharp_score > blurry_score, (
            f"Expected sharp ({sharp_score:.2f}) > blurry ({blurry_score:.2f})"
        )

    def test_returns_float(self):
        """Return type must be float."""
        score = compute_blur_score_laplacian(_make_sharp_bgr())
        assert isinstance(score, float)

    def test_score_nonnegative(self):
        """Variance is always non-negative."""
        for img in (_make_sharp_bgr(), _make_blurry_bgr()):
            assert compute_blur_score_laplacian(img) >= 0.0

    def test_from_file_path(self, tmp_path):
        """Accepts a file path and loads the image automatically."""
        img_path = str(tmp_path / "test.png")
        cv2.imwrite(img_path, _make_sharp_bgr())
        score = compute_blur_score_laplacian(img_path)
        assert isinstance(score, float)
        assert score >= 0.0

    def test_invalid_path_raises(self):
        """A non-existent path must raise ValueError."""
        with pytest.raises(ValueError, match="Could not load image"):
            compute_blur_score_laplacian("/nonexistent/path/image.png")

    def test_uniform_image_zero_score(self):
        """A perfectly uniform image has zero Laplacian variance."""
        uniform = np.full((64, 64, 3), 128, dtype=np.uint8)
        score = compute_blur_score_laplacian(uniform)
        assert score == pytest.approx(0.0, abs=1e-6)


class TestBlurLabelAndColor:
    """Tests for blur_label_and_color."""

    def test_sharp_label_above_threshold(self):
        label, color = blur_label_and_color(100.0)
        assert label == "Sharp"
        assert color == "green"

    def test_blur_label_below_threshold(self):
        label, color = blur_label_and_color(99.9)
        assert label == "Blur"
        assert color == "red"

    def test_blur_label_zero(self):
        label, color = blur_label_and_color(0.0)
        assert label == "Blur"
        assert color == "red"

    def test_sharp_label_high_score(self):
        label, color = blur_label_and_color(500.0)
        assert label == "Sharp"
        assert color == "green"


class TestNormalizeScore:
    """Tests for normalize_score."""

    def test_zero_maps_to_zero(self):
        assert normalize_score(0.0) == pytest.approx(0.0)

    def test_cap_maps_to_hundred(self):
        assert normalize_score(400.0) == pytest.approx(100.0)

    def test_above_cap_clamped_to_hundred(self):
        assert normalize_score(800.0) == pytest.approx(100.0)

    def test_mid_value(self):
        assert normalize_score(200.0) == pytest.approx(50.0)

    def test_custom_cap(self):
        assert normalize_score(50.0, cap=200.0) == pytest.approx(25.0)

    def test_zero_cap_returns_zero(self):
        assert normalize_score(100.0, cap=0.0) == pytest.approx(0.0)
