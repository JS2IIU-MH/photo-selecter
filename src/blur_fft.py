"""FFT-based blur / sharpness detection module.

This module provides a focus metric based on the 2-D Fast Fourier Transform
(FFT).  Sharp images contain significant high-frequency energy (edges,
textures), while blurry images concentrate energy near the DC / low-frequency
region.  The ratio of high-frequency magnitude to total magnitude therefore
serves as a reliable, fast sharpness score.

Typical usage::

    from blur_fft import compute_blur_score_fft, normalize_score, blur_label_and_color

    raw   = compute_blur_score_fft("photo.jpg")   # 0.0 – 1.0
    norm  = normalize_score(raw)                  # 0.0 – 100.0
    label, color = blur_label_and_color(norm)     # e.g. ("Sharp", "green")
"""

from __future__ import annotations

from typing import Tuple, Union

import cv2
import numpy as np


def compute_blur_score_fft(image: Union[np.ndarray, str]) -> float:
    """Compute a sharpness score using an FFT-based focus metric.

    The image is converted to grayscale, then the 2-D FFT magnitude spectrum
    is computed.  The score is the proportion of energy that falls *outside* a
    low-frequency central region — higher values indicate a sharper image.

    Args:
        image: A NumPy BGR image array *or* a file-path string pointing to an
               image file readable by OpenCV.

    Returns:
        A float in ``[0.0, 1.0]`` representing the proportion of
        high-frequency energy.  Higher means sharper.

    Raises:
        ValueError: If *image* is a path string and the file cannot be loaded.
    """
    if isinstance(image, str):
        img_bgr = cv2.imread(image)
        if img_bgr is None:
            raise ValueError(f"Could not load image from path: {image}")
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    else:
        arr = np.asarray(image)
        if arr.ndim == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        else:
            gray = arr

    f = np.fft.fft2(gray.astype(np.float32))
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)

    h, w = magnitude.shape
    cy, cx = h // 2, w // 2

    # Divide the shorter dimension by 8 to define the low-frequency region.
    # This empirically captures DC and the lowest octave of frequencies while
    # leaving the majority (~95 %) of the spectrum available as "high-frequency".
    mask_radius = max(min(h, w) // 8, 1)
    yy, xx = np.ogrid[:h, :w]
    low_freq_mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= mask_radius ** 2

    total_energy = float(np.sum(magnitude))
    if total_energy == 0.0:
        return 0.0

    high_freq_energy = float(np.sum(magnitude[~low_freq_mask]))
    return high_freq_energy / total_energy


def normalize_score(score: float, cap: float = 1.0) -> float:
    """Normalise a raw FFT blur score to the range 0 – 100.

    Args:
        score: Raw score returned by :func:`compute_blur_score_fft`
               (typically in ``[0.0, 1.0]``).
        cap:   The value that maps to 100 after normalisation.
               Defaults to ``1.0`` (the theoretical maximum of the raw score).

    Returns:
        A float in ``[0.0, 100.0]``.
    """
    if cap <= 0:
        return 0.0
    return min(score / cap, 1.0) * 100.0


def blur_label_and_color(score: float) -> Tuple[str, str]:
    """Map a *normalised* FFT score (0 – 100) to a label and display colour.

    The labels and colours are intentionally consistent with the Laplacian
    implementation so that both methods produce compatible UI overlays.

    Args:
        score: Normalised sharpness score in ``[0.0, 100.0]``.

    Returns:
        A tuple ``(label, color)`` where *color* is a Pillow / CSS colour
        string.

        +-----------+------------------+--------+
        | score     | label            | color  |
        +===========+==================+========+
        | < 50      | ``"Blur"``       | red    |
        +-----------+------------------+--------+
        | 50 – 74   | ``"Maybe Blur"`` | orange |
        +-----------+------------------+--------+
        | ≥ 75      | ``"Sharp"``      | green  |
        +-----------+------------------+--------+
    """
    if score < 50.0:
        return ("Blur", "red")
    if score < 75.0:
        return ("Maybe Blur", "orange")
    return ("Sharp", "green")
