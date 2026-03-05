"""FFT-based blur detection module for picsel.

This module provides functions to measure image sharpness using the
Fast Fourier Transform (FFT).  A sharper image has more high-frequency
energy, so the proportion of high-frequency magnitude to total magnitude
is used as the focus metric.
"""

from __future__ import annotations

from typing import Tuple, Union

import cv2
import numpy as np


def compute_blur_score_fft(image: Union[np.ndarray, str]) -> float:
    """Compute an FFT-based sharpness score for an image.

    The score is the ratio of high-frequency energy to total energy in
    the magnitude spectrum of the grayscale image.  Higher values
    indicate a sharper image.

    Args:
        image: A NumPy array in BGR format (as returned by ``cv2.imread``)
            **or** a file path string.  If a file path is supplied the
            image is loaded with ``cv2.imread``.

    Returns:
        A float in the range [0.0, 1.0] representing the proportion of
        high-frequency energy.  Returns 0.0 when the image cannot be
        read or is empty.
    """
    if isinstance(image, str):
        img = cv2.imread(image)
        if img is None:
            return 0.0
    else:
        img = image

    if img is None or img.size == 0:
        return 0.0

    # Convert to grayscale
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.astype(np.float64)

    gray = gray.astype(np.float64)

    # 2-D FFT and magnitude spectrum
    fft = np.fft.fft2(gray)
    fft_shifted = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shifted)

    total_energy = magnitude.sum()
    if total_energy == 0.0:
        return 0.0

    # Define a central low-frequency mask (radius = 10 % of the smaller
    # image dimension).  Energy *outside* this mask is "high-frequency".
    rows, cols = gray.shape
    crow, ccol = rows // 2, cols // 2
    radius = int(min(rows, cols) * 0.1)

    # Create mask for the low-frequency region
    y_grid, x_grid = np.ogrid[:rows, :cols]
    dist_from_center = np.sqrt((y_grid - crow) ** 2 + (x_grid - ccol) ** 2)
    low_freq_mask = dist_from_center <= radius

    high_freq_energy = magnitude[~low_freq_mask].sum()
    score: float = float(high_freq_energy / total_energy)
    return score


def blur_label_and_color(score: float) -> Tuple[str, str]:
    """Return a human-readable label and display colour for an FFT score.

    Labels and colours are kept consistent with the Laplacian
    implementation so that both methods produce visually uniform badges.

    Args:
        score: Normalised sharpness score in the range [0, 100].

    Returns:
        A ``(label, color)`` tuple where *label* is one of
        ``"Sharp"``, ``"OK"``, or ``"Blur"``, and *color* is a CSS-style
        colour string (``"green"``, ``"orange"``, or ``"red"``).
    """
    if score >= 60:
        return ("Sharp", "green")
    if score >= 30:
        return ("OK", "orange")
    return ("Blur", "red")


def normalize_score(score: float, cap: float = 1.0) -> float:
    """Normalise a raw FFT score to the 0–100 range.

    Args:
        score: Raw FFT sharpness score (proportion of high-frequency
            energy), typically in [0.0, 1.0].
        cap: The raw score value that maps to 100.  Scores above *cap*
            are clamped to 100.  Defaults to ``1.0``.

    Returns:
        A float in [0.0, 100.0].
    """
    if cap <= 0:
        return 0.0
    normalised = (score / cap) * 100.0
    return float(min(max(normalised, 0.0), 100.0))
