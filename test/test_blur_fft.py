"""Unit tests for src/blur_fft.py.

All tests are self-contained and synthesise images programmatically so that
no external image files are required.
"""

import sys
import os
import pytest
import numpy as np
import cv2

# Ensure the src directory is on the path so we can import blur_fft directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from blur_fft import compute_blur_score_fft, normalize_score, blur_label_and_color


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sharp_image(size: int = 128, seed: int = 42) -> np.ndarray:
    """Return a BGR image filled with random noise.

    Random noise has a flat (white-noise) power spectrum and therefore
    contains maximal high-frequency energy, making it an unambiguously sharp
    reference image for FFT-based metrics.

    Args:
        size: Side length of the square image in pixels.
        seed: NumPy random seed for reproducible test results.
    """
    rng = np.random.default_rng(seed)
    gray = rng.integers(0, 256, (size, size), dtype=np.uint8)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _make_blurry_image(sharp_bgr: np.ndarray, ksize: int = 41) -> np.ndarray:
    """Apply a large Gaussian blur to *sharp_bgr* to simulate an out-of-focus image.

    A kernel size of 41 (sigma ≈ 7 pixels) provides strong attenuation of
    frequencies above ~1/14 cycles/pixel, which is well within the high-frequency
    region detected by :func:`compute_blur_score_fft`.
    """
    return cv2.GaussianBlur(sharp_bgr, (ksize, ksize), 0)


# ---------------------------------------------------------------------------
# compute_blur_score_fft
# ---------------------------------------------------------------------------

class TestComputeBlurScoreFft:
    """Tests for :func:`compute_blur_score_fft`."""

    def test_sharp_higher_than_blurry(self):
        """Sharp image must score higher than its blurred counterpart."""
        sharp = _make_sharp_image()
        blurry = _make_blurry_image(sharp)

        score_sharp = compute_blur_score_fft(sharp)
        score_blurry = compute_blur_score_fft(blurry)

        assert score_sharp > score_blurry, (
            f"Expected sharp ({score_sharp:.4f}) > blurry ({score_blurry:.4f})"
        )

    def test_score_range(self):
        """Raw score must be in [0.0, 1.0]."""
        sharp = _make_sharp_image()
        score = compute_blur_score_fft(sharp)
        assert 0.0 <= score <= 1.0

    def test_accepts_file_path(self, tmp_path):
        """Function must accept a file-path string and return a valid score."""
        sharp = _make_sharp_image()
        path = str(tmp_path / "sharp.png")
        cv2.imwrite(path, sharp)

        score = compute_blur_score_fft(path)
        assert 0.0 <= score <= 1.0

    def test_invalid_path_raises(self):
        """A non-existent file path must raise :class:`ValueError`."""
        with pytest.raises(ValueError):
            compute_blur_score_fft("/nonexistent/path/image.jpg")

    def test_accepts_grayscale_array(self):
        """Grayscale (2-D) numpy arrays must be handled without error."""
        gray = np.random.randint(0, 256, (64, 64), dtype=np.uint8)
        score = compute_blur_score_fft(gray)
        assert 0.0 <= score <= 1.0

    def test_uniform_image_score(self):
        """A uniform (all-white) image has no high-frequency content; score ≈ 0."""
        uniform = np.full((64, 64, 3), 255, dtype=np.uint8)
        score = compute_blur_score_fft(uniform)
        # Most energy is in the DC component; high-frequency ratio should be low.
        assert score < 0.5

    def test_increasing_blur_decreasing_score(self):
        """Progressively stronger blur must produce monotonically decreasing scores."""
        sharp = _make_sharp_image(128)
        kernel_sizes = [3, 9, 21, 41]
        scores = [compute_blur_score_fft(_make_blurry_image(sharp, k))
                  for k in kernel_sizes]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Score did not decrease: k={kernel_sizes[i]} gave {scores[i]:.4f}, "
                f"k={kernel_sizes[i+1]} gave {scores[i+1]:.4f}"
            )


# ---------------------------------------------------------------------------
# normalize_score
# ---------------------------------------------------------------------------

class TestNormalizeScore:
    """Tests for :func:`normalize_score`."""

    def test_zero(self):
        assert normalize_score(0.0) == pytest.approx(0.0)

    def test_one(self):
        assert normalize_score(1.0) == pytest.approx(100.0)

    def test_half(self):
        assert normalize_score(0.5) == pytest.approx(50.0)

    def test_clamped_above_cap(self):
        """Scores above *cap* must be clamped to 100."""
        assert normalize_score(2.0, cap=1.0) == pytest.approx(100.0)

    def test_custom_cap(self):
        assert normalize_score(50.0, cap=200.0) == pytest.approx(25.0)

    def test_invalid_cap_returns_zero(self):
        assert normalize_score(0.5, cap=0.0) == pytest.approx(0.0)
        assert normalize_score(0.5, cap=-1.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# blur_label_and_color
# ---------------------------------------------------------------------------

class TestBlurLabelAndColor:
    """Tests for :func:`blur_label_and_color`."""

    def test_blur_region(self):
        label, color = blur_label_and_color(30.0)
        assert label == 'Blur'
        assert color == 'red'

    def test_boundary_blur(self):
        label, color = blur_label_and_color(0.0)
        assert label == 'Blur'

    def test_maybe_blur_region(self):
        label, color = blur_label_and_color(60.0)
        assert label == 'Maybe Blur'
        assert color == 'orange'

    def test_sharp_region(self):
        label, color = blur_label_and_color(80.0)
        assert label == 'Sharp'
        assert color == 'green'

    def test_boundary_sharp(self):
        label, color = blur_label_and_color(100.0)
        assert label == 'Sharp'

    def test_return_type(self):
        result = blur_label_and_color(50.0)
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Integration: sharp vs blurry end-to-end
# ---------------------------------------------------------------------------

class TestEndToEnd:
    """End-to-end tests combining all three public functions."""

    def test_sharp_image_labeled_sharp(self):
        """A random-noise image (maximally sharp in FFT terms) must not be labelled 'Blur'."""
        sharp = _make_sharp_image()
        raw = compute_blur_score_fft(sharp)
        norm = normalize_score(raw)
        label, _ = blur_label_and_color(norm)
        assert label != 'Blur', (
            f"Sharp image incorrectly labelled 'Blur' (norm={norm:.1f})"
        )

    def test_heavily_blurred_image_labeled_blur(self):
        """A heavily blurred image should be labelled 'Blur'."""
        sharp = _make_sharp_image(128)
        blurry = _make_blurry_image(sharp, ksize=61)
        raw = compute_blur_score_fft(blurry)
        norm = normalize_score(raw)
        label, _ = blur_label_and_color(norm)
        assert label == 'Blur', (
            f"Blurry image not labelled 'Blur' (norm={norm:.1f})"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
