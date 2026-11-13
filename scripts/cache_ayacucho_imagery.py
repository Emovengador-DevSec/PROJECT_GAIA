"""Genera la imagen Landsat de contexto de Ayacucho desde teselas públicas NASA GIBS."""
from __future__ import annotations

import json
import math
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from rasterio import open as raster_open
from rasterio.errors import NotGeoreferencedWarning
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject, transform_bounds

ROOT = Path(__file__).resolve().parents[1] / "apps/web/public/globe"
LAYER = "Landsat_WELD_CorrectedReflectance_TrueColor_Global_Annual"
DATE = "2000-12-01"
BOUNDS = (-74.7, -13.65, -73.6, -12.55)
ZOOM = 11
SIZE = 256
RADIUS = 20037508.342789244
BASE = (f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{LAYER}/default/{DATE}/"
        f"GoogleMapsCompatible_Level12/{ZOOM}")


def fetch_tile(tile: tuple[int, int]) -> tuple[int, int, np.ndarray]:
    x, y = tile
    with urlopen(f"{BASE}/{y}/{x}.jpeg", timeout=20) as response:
        data = response.read(1_000_001)
    if len(data) > 1_000_000 or not data.startswith(b"\xff\xd8"):
        raise ValueError(f"Imagen no válida en {x}/{y}")
    with MemoryFile(data) as source, source.open() as image:
        pixels = image.read()
    if pixels.shape != (3, SIZE, SIZE):
        raise ValueError(f"Dimensiones inesperadas en {x}/{y}")
    return x, y, pixels


def main() -> None:
    warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)
    west, south, east, north = transform_bounds("EPSG:4326", "EPSG:3857", *BOUNDS)
    tile_span = 2 * RADIUS / 2**ZOOM
    left = math.floor((west + RADIUS) / tile_span)
    right = math.floor((east + RADIUS) / tile_span)
    top = math.floor((RADIUS - north) / tile_span)
    bottom = math.floor((RADIUS - south) / tile_span)
    width, height = (right - left + 1) * SIZE, (bottom - top + 1) * SIZE
    mosaic = np.zeros((3, height, width), dtype=np.uint8)
    tiles = [(x, y) for y in range(top, bottom + 1) for x in range(left, right + 1)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        for x, y, pixels in executor.map(fetch_tile, tiles):
            dx, dy = (x - left) * SIZE, (y - top) * SIZE
            mosaic[:, dy:dy + SIZE, dx:dx + SIZE] = pixels
    source_transform = from_bounds(left * tile_span - RADIUS, RADIUS - (bottom + 1) * tile_span,
                                   (right + 1) * tile_span - RADIUS, RADIUS - top * tile_span, width, height)
    resolution = 1600
    output = np.zeros((3, resolution, resolution), dtype=np.uint8)
    reproject(mosaic, output, src_crs="EPSG:3857", src_transform=source_transform,
              dst_crs="EPSG:4326", dst_transform=from_bounds(*BOUNDS, resolution, resolution),
              resampling=Resampling.bilinear)
    with raster_open(ROOT / "ayacucho-landsat.jpg", "w", driver="JPEG", width=resolution,
                     height=resolution, count=3, dtype="uint8", quality=90) as target:
        target.write(output)
    metadata = {"bbox": BOUNDS, "product": LAYER, "date": DATE, "source": "NASA GIBS · Landsat WELD",
                "capabilities": "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml"}
    (ROOT / "ayacucho-landsat.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Landsat Ayacucho: {len(tiles)} teselas, imagen local {resolution}×{resolution}, fecha {DATE}")


if __name__ == "__main__":
    main()
