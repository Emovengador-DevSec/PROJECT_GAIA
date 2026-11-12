"""Escritura de Cloud Optimized GeoTIFF."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling


def write_cog(path: Path, arr: np.ndarray, transform, epsg: int, nodata=np.nan,
              dtype="float32") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = dict(driver="COG", height=arr.shape[0], width=arr.shape[1], count=1,
                   dtype=dtype, crs=f"EPSG:{epsg}", transform=transform, nodata=nodata,
                   compress="DEFLATE", blocksize=512, overview_resampling="average")
    try:
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(arr.astype(dtype), 1)
    except Exception:  # noqa: BLE001
        # GDAL antiguo sin driver COG: GTiff en mosaicos + vistas reducidas
        profile.update(driver="GTiff", tiled=True, blockxsize=512, blockysize=512)
        profile.pop("blocksize"); profile.pop("overview_resampling")
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(arr.astype(dtype), 1)
            dst.build_overviews([2, 4, 8, 16], Resampling.average)
    return path
