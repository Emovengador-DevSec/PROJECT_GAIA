"""Conversiones físicas de retrodispersión."""
from __future__ import annotations

import numpy as np


def to_db(linear: np.ndarray, floor: float = 1e-6) -> np.ndarray:
    """Potencia lineal -> decibelios. Valores <=0 o NaN quedan como NaN."""
    lin = np.where(np.isfinite(linear) & (linear > 0), linear, np.nan)
    return (10.0 * np.log10(np.maximum(lin, floor))).astype("float32")


def diff_db(before_db: np.ndarray, after_db: np.ndarray) -> np.ndarray:
    """Cambio = después - antes (dB). Negativo en HV suele indicar pérdida de vegetación."""
    if before_db.shape != after_db.shape:
        raise ValueError("Las capas deben estar alineadas en la misma rejilla.")
    return (after_db - before_db).astype("float32")


def boxcar(arr: np.ndarray, size: int = 3) -> np.ndarray:
    """Promedio móvil simple para reducir moteado (speckle), ignorando NaN."""
    if size <= 1:
        return arr
    pad = size // 2
    a = np.pad(arr, pad, mode="edge")
    valid = np.isfinite(a)
    a0 = np.where(valid, a, 0.0)
    out = np.zeros_like(arr, dtype="float64")
    cnt = np.zeros_like(arr, dtype="float64")
    for dy in range(size):
        for dx in range(size):
            out += a0[dy:dy + arr.shape[0], dx:dx + arr.shape[1]]
            cnt += valid[dy:dy + arr.shape[0], dx:dx + arr.shape[1]]
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(cnt > 0, out / cnt, np.nan).astype("float32")
