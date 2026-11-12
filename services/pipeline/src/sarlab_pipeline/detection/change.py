"""Detección de cambio con umbral estadístico robusto (no valores fijos arbitrarios)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ChangeResult:
    loss: np.ndarray        # bool: caída significativa
    gain: np.ndarray        # bool: subida significativa
    threshold_db: float
    median: float
    robust_sigma: float


def robust_threshold(diff: np.ndarray, k_sigma: float = 3.0) -> ChangeResult:
    v = diff[np.isfinite(diff)]
    if v.size == 0:
        raise ValueError("Sin píxeles válidos para calcular el umbral.")
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    sigma = 1.4826 * mad if mad > 0 else float(np.std(v)) or 1e-6
    thr = k_sigma * sigma
    with np.errstate(invalid="ignore"):
        loss = (diff - med) < -thr
        gain = (diff - med) > thr
    return ChangeResult(loss=loss, gain=gain, threshold_db=thr, median=med, robust_sigma=sigma)


def polygons(mask: np.ndarray, transform, min_pixels: int = 25, epsg: int | None = None):
    """Convierte la máscara de cambio en polígonos GeoJSON (en el CRS del producto)."""
    from rasterio.features import shapes

    feats = []
    labeled, n = _label(mask)
    if n == 0:
        return feats
    sizes = np.bincount(labeled.ravel())
    keep = np.isin(labeled, np.where(sizes >= min_pixels)[0][1:])
    for geom, val in shapes(keep.astype("uint8"), mask=keep, transform=transform):
        if val:
            feats.append({"type": "Feature", "geometry": geom, "properties": {}})
    return feats


def _label(mask: np.ndarray):
    from scipy import ndimage
    return ndimage.label(mask)
