"""Blur detection using the Variance of Laplacian focus metric."""

from __future__ import annotations

import os
from typing import Tuple, Union

import cv2
import numpy as np


def compute_blur_score_laplacian(image: Union[str, np.ndarray]) -> float:
    """Compute a blur score using the Variance of Laplacian method.

    A higher score indicates a sharper image.

    Args:
        image: A file path (str) to a BGR image, or a NumPy BGR image array.

    Returns:
        float: Variance of the Laplacian of the grayscale image.

    Raises:
        ValueError: If a file path is given but the image cannot be loaded.
    """
    if isinstance(image, str):
        img = cv2.imread(image)
        if img is None:
            raise ValueError(f"Could not load image from path: {image}")
    else:
        img = np.asarray(image)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def blur_label_and_color(score: float) -> Tuple[str, str]:
    """Return a human-readable label and display colour for a blur score.

    The label and colour scheme is consistent with other blur detection
    implementations in the project.

    Args:
        score: Variance of Laplacian score (higher = sharper).

    Returns:
        Tuple[str, str]: ``(label, color)`` where *color* is a CSS-compatible
        colour name or hex string.
    """
    if score >= 100.0:
        return ("Sharp", "green")
    return ("Blur", "red")


def normalize_score(score: float, cap: float = 400.0) -> float:
    """Normalize a raw Laplacian variance score to the range 0–100.

    Args:
        score: Raw Variance of Laplacian score.
        cap: Value that maps to 100 in the normalized range (default 400.0).

    Returns:
        float: Score clamped and scaled to the interval [0, 100].
    """
    if cap <= 0:
        return 0.0
    return min(score / cap * 100.0, 100.0)
