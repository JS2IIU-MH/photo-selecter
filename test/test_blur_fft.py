"""Unit tests for src/blur_fft.py.

All tests are self-contained and synthesise images programmatically so
that no external image files are required.
"""

import sys
import os

import numpy as np
import pytest

# Ensure the src directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from blur_fft import (
    compute_blur_score_fft,
    blur_label_and_color,
    normalize_score,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sharp_bgr(size: int = 256) -> np.ndarray:
    """Return a synthetic BGR image with sharp edges (checkerboard)."""
    tile = 16
    row = np.arange(size)
    col = np.arange(size)
    c, r = np.meshgrid(col, row)
    gray = (((r // tile) + (c // tile)) % 2 * 255).astype(np.uint8)
    return np.stack([gray, gray, gray], axis=-1)


def _make_blurred_bgr(size: int = 256, sigma: float = 15.0) -> np.ndarray:
    """Return a Gaussian-blurred version of the checkerboard image."""
    import cv2
    sharp = _make_sharp_bgr(size)
    k = int(sigma * 6) | 1  # odd kernel size
    return cv2.GaussianBlur(sharp, (k, k), sigma)


# ---------------------------------------------------------------------------
# compute_blur_score_fft
# ---------------------------------------------------------------------------

class TestComputeBlurScoreFft:
    def test_sharp_higher_than_blurred(self):
        """Sharp image must score higher than blurred image."""
        sharp = _make_sharp_bgr()
        blurred = _make_blurred_bgr()
        score_sharp = compute_blur_score_fft(sharp)
        score_blurred = compute_blur_score_fft(blurred)
        assert score_sharp > score_blurred, (
            f"Expected sharp ({score_sharp:.4f}) > blurred ({score_blurred:.4f})"
        )

    def test_score_in_unit_range(self):
        """Score must be in [0.0, 1.0]."""
        for img in (_make_sharp_bgr(), _make_blurred_bgr()):
            score = compute_blur_score_fft(img)
            assert 0.0 <= score <= 1.0, f"Score {score} out of [0, 1]"

    def test_file_path_input(self, tmp_path):
        """Passing a file path should produce the same score as a BGR array."""
        import cv2
        img = _make_sharp_bgr()
        path = str(tmp_path / "sharp.png")
        cv2.imwrite(path, img)
        score_array = compute_blur_score_fft(img)
        score_file = compute_blur_score_fft(path)
        assert abs(score_array - score_file) < 1e-6

    def test_missing_file_returns_zero(self):
        """A non-existent file path should return 0.0 without raising."""
        score = compute_blur_score_fft("/nonexistent/path/image.jpg")
        assert score == 0.0

    def test_empty_array_returns_zero(self):
        """An empty NumPy array should return 0.0 without raising."""
        score = compute_blur_score_fft(np.zeros((0, 0, 3), dtype=np.uint8))
        assert score == 0.0

    def test_grayscale_array_input(self):
        """A 2-D (grayscale) array should be handled gracefully."""
        gray = _make_sharp_bgr()[:, :, 0]  # 2-D
        score = compute_blur_score_fft(gray)
        assert 0.0 <= score <= 1.0

    def test_uniform_image_low_score(self):
        """A completely uniform image has no edges → low high-frequency energy."""
        uniform = np.full((128, 128, 3), 128, dtype=np.uint8)
        score = compute_blur_score_fft(uniform)
        # A uniform image has only DC component → score should be very low
        assert score < 0.1, f"Uniform image score {score} should be < 0.1"


# ---------------------------------------------------------------------------
# blur_label_and_color
# ---------------------------------------------------------------------------

class TestBlurLabelAndColor:
    def test_sharp_label(self):
        label, color = blur_label_and_color(70)
        assert label == "Sharp"
        assert color == "green"

    def test_ok_label(self):
        label, color = blur_label_and_color(45)
        assert label == "OK"
        assert color == "orange"

    def test_blur_label(self):
        label, color = blur_label_and_color(10)
        assert label == "Blur"
        assert color == "red"

    def test_boundary_sharp(self):
        label, _ = blur_label_and_color(60)
        assert label == "Sharp"

    def test_boundary_ok(self):
        label, _ = blur_label_and_color(30)
        assert label == "OK"

    def test_boundary_blur(self):
        label, _ = blur_label_and_color(29.9)
        assert label == "Blur"

    def test_zero_score(self):
        label, color = blur_label_and_color(0)
        assert label == "Blur"
        assert color == "red"

    def test_hundred_score(self):
        label, color = blur_label_and_color(100)
        assert label == "Sharp"
        assert color == "green"


# ---------------------------------------------------------------------------
# normalize_score
# ---------------------------------------------------------------------------

class TestNormalizeScore:
    def test_zero_maps_to_zero(self):
        assert normalize_score(0.0) == 0.0

    def test_cap_maps_to_hundred(self):
        assert normalize_score(1.0, cap=1.0) == 100.0

    def test_half_cap_maps_to_fifty(self):
        assert abs(normalize_score(0.5, cap=1.0) - 50.0) < 1e-9

    def test_above_cap_clamped_to_hundred(self):
        assert normalize_score(2.0, cap=1.0) == 100.0

    def test_negative_clamped_to_zero(self):
        assert normalize_score(-0.5) == 0.0

    def test_custom_cap(self):
        assert abs(normalize_score(0.5, cap=0.5) - 100.0) < 1e-9

    def test_zero_cap_returns_zero(self):
        assert normalize_score(0.5, cap=0.0) == 0.0


# ---------------------------------------------------------------------------
# Integration: sharp vs blurred using normalize_score + blur_label_and_color
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_sharp_image_gets_non_blur_label(self):
        """A clearly sharp synthetic image should not get the 'Blur' label."""
        sharp = _make_sharp_bgr()
        raw = compute_blur_score_fft(sharp)
        norm = normalize_score(raw)
        label, _ = blur_label_and_color(norm)
        assert label in ("Sharp", "OK"), (
            f"Sharp image incorrectly labelled '{label}' (norm={norm:.1f})"
        )

    def test_blurred_image_gets_blur_label(self):
        """A heavily blurred image should get the 'Blur' label."""
        blurred = _make_blurred_bgr(sigma=40.0)
        raw = compute_blur_score_fft(blurred)
        norm = normalize_score(raw)
        label, _ = blur_label_and_color(norm)
        assert label == "Blur", (
            f"Blurred image incorrectly labelled '{label}' (norm={norm:.1f})"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
