"""NISAR L3 SME2 (soil moisture) reader.

Paths confirmed with `sarlab inspect` on 2026-11-14 (see docs/data-notes.md):
  science/LSAR/SME2/grids/soilMoisture           float32, m3/m3, _FillValue -9999
  science/LSAR/SME2/grids/retrievalQualityFlag   int16, bit 0: 0 = recommended
  science/LSAR/SME2/grids/xCoordinates|yCoordinates  pixel centres, metres
  science/LSAR/SME2/grids/projection             attr epsg_code = 6933 (EASE-Grid 2.0)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
from rasterio.transform import from_origin

GRID = "science/LSAR/SME2/grids"


@dataclass
class SoilMoisture:
    data: np.ndarray  # m3/m3, NaN where missing or not recommended
    transform: object
    epsg: int
    recommended_fraction: float


def read_soil_moisture(path: Path) -> SoilMoisture:
    with h5py.File(path, "r") as f:
        g = f[GRID]
        sm = g["soilMoisture"][:].astype("float32")
        fill = g["soilMoisture"].attrs.get("_FillValue", -9999.0)
        flag = g["retrievalQualityFlag"][:]
        x = g["xCoordinates"][:]
        y = g["yCoordinates"][:]
        epsg = int(g["projection"].attrs["epsg_code"])
    valid = np.isfinite(sm) & (sm != fill)
    recommended = valid & (flag >= 0) & ((flag & 1) == 0)
    out = np.where(recommended, sm, np.nan).astype("float32")
    dx = float(x[1] - x[0])
    dy = float(y[0] - y[1])  # positive; y decreases downward
    transform = from_origin(float(x[0]) - dx / 2, float(y[0]) + dy / 2, dx, dy)
    frac = float(recommended.sum() / valid.sum()) if valid.any() else 0.0
    return SoilMoisture(out, transform, epsg, frac)
