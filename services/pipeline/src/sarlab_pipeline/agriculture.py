"""Slope exposure of mapped cropland changes, without inferring bare soil or erosion."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer

from . import exposure

FIELDS = ("cropland_low_slope_ha", "cropland_steep_ha", "cropland_slope_unknown_ha")
SLOPE_THRESHOLD_DEG = 15


def slope_degrees(elevation: np.ndarray, resolution: float) -> np.ndarray:
    if resolution <= 0 or min(elevation.shape) < 3:
        raise ValueError("La pendiente requiere una rejilla métrica de al menos 3×3.")
    north, east = np.gradient(elevation.astype("float64"), resolution, resolution)
    result = np.degrees(np.arctan(np.hypot(north, east))).astype("float32")
    result[[0, -1], :] = np.nan
    result[:, [0, -1]] = np.nan
    return result


def slope_exposure(geometry: dict, landcover: Path, slope: Path, target_ha: float) -> dict:
    values, fractions, rows, affine, crs, _, cols = exposure._weighted_cells(
        landcover, geometry, with_columns=True)
    crop = (values == 40) & (fractions > 0)
    if not crop.any() or not target_ha:
        return dict(zip(FIELDS, [0.0, 0.0, round(target_ha, 3)], strict=True))
    rows, cols, fractions = rows[crop], cols[crop], fractions[crop]
    if crs.is_geographic:
        areas = []
        for row in rows:
            west, north = affine * (0, row)
            east, south = affine * (1, row + 1)
            area, _ = exposure.WGS84.polygon_area_perimeter(
                [west, east, east, west], [north, north, south, south])
            areas.append(abs(area) / 1e4)
        area = fractions * np.asarray(areas)
    else:
        area = fractions * abs(affine.a * affine.e) / 1e4
    x = affine.c + affine.a * (cols + .5)
    y = affine.f + affine.e * (rows + .5)
    with rasterio.open(slope) as terrain:
        tx, ty = Transformer.from_crs(crs, terrain.crs, always_xy=True).transform(x, y)
        samples = np.array([item[0] for item in terrain.sample(zip(tx, ty, strict=True))])
        valid = np.isfinite(samples) & (samples >= 0) & (samples <= 90)
    shares = np.array([area[valid & (samples <= SLOPE_THRESHOLD_DEG)].sum(),
                       area[valid & (samples > SLOPE_THRESHOLD_DEG)].sum(),
                       area[~valid].sum()]) / area.sum()
    units = shares * round(target_ha * 1000)
    allocated = np.floor(units).astype(int)
    remainder = round(target_ha * 1000) - allocated.sum()
    allocated[np.argsort(-(units - allocated))[:remainder]] += 1
    return dict(zip(FIELDS, (allocated / 1000).tolist(), strict=True))
