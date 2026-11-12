"""Máscaras y estadística de calidad."""
from __future__ import annotations

import numpy as np


def valid_fraction(arr: np.ndarray) -> float:
    return float(np.isfinite(arr).mean()) if arr.size else 0.0


def apply_mask(arr: np.ndarray, keep: np.ndarray) -> np.ndarray:
    return np.where(keep, arr, np.nan).astype("float32")


def coherence_mask(coherence: np.ndarray, threshold: float) -> np.ndarray:
    return np.isfinite(coherence) & (coherence >= threshold)
