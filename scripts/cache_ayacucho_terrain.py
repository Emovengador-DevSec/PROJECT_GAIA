"""Recorta alturas Mapzen Terrain Tiles para la vista local de los Andes."""
from __future__ import annotations

import json
import math
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from urllib.request import urlopen

import numpy as np
from cache_ayacucho_imagery import RADIUS, ROOT, SIZE
from rasterio.errors import NotGeoreferencedWarning
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject, transform_bounds

BOUNDS = (-76.0, -14.5, -72.5, -11.7)
ZOOM = 9
GRID = 641
URL = "https://elevation-tiles-prod.s3.amazonaws.com/terrarium"


def download(tile: tuple[int, int]):
    x, y = tile
    with urlopen(f"{URL}/{ZOOM}/{x}/{y}.png", timeout=20) as response:
        body = response.read(1_000_001)
    if len(body) > 1_000_000 or not body.startswith(b"\x89PNG"):
        raise ValueError(f"Tesela inválida {x}/{y}")
    with MemoryFile(body) as file, file.open() as source:
        red, green, blue = source.read((1, 2, 3)).astype("float32")
    return x, y, red * 256 + green + blue / 256 - 32768


def main() -> None:
    warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)
    west, south, east, north = transform_bounds("EPSG:4326", "EPSG:3857", *BOUNDS)
    span = 2 * RADIUS / 2**ZOOM
    left, right = math.floor((west + RADIUS) / span), math.floor((east + RADIUS) / span)
    top, bottom = math.floor((RADIUS - north) / span), math.floor((RADIUS - south) / span)
    width, height = (right - left + 1) * SIZE, (bottom - top + 1) * SIZE
    mosaic = np.zeros((height, width), dtype=np.float32)
    tiles = [(x, y) for y in range(top, bottom + 1) for x in range(left, right + 1)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for x, y, data in pool.map(download, tiles):
            dx, dy = (x - left) * SIZE, (y - top) * SIZE
            mosaic[dy:dy + SIZE, dx:dx + SIZE] = data
    transform = from_bounds(left * span - RADIUS, RADIUS - (bottom + 1) * span,
                            (right + 1) * span - RADIUS, RADIUS - top * span, width, height)
    grid = np.zeros((GRID, GRID), dtype=np.float32)
    reproject(mosaic, grid, src_crs="EPSG:3857", src_transform=transform, dst_crs="EPSG:4326",
              dst_transform=from_bounds(*BOUNDS, GRID, GRID), resampling=Resampling.bilinear)
    if not np.isfinite(grid).all() or grid.max() < 3000:
        raise ValueError("Alturas incompletas o fuera de la zona esperada")
    (ROOT / "ayacucho-terrain.bin").write_bytes(np.rint(grid).astype("<i2").tobytes())
    metadata = {"bbox": BOUNDS, "width": GRID, "height": GRID, "unit": "m", "encoding": "int16le",
                "retrieved_at": datetime.now(UTC).isoformat(), "source": "Mapzen Terrain Tiles",
                "source_url": "https://registry.opendata.aws/terrain-tiles/",
                "attribution_url": "https://github.com/tilezen/joerd/blob/master/docs/attribution.md"}
    (ROOT / "ayacucho-terrain.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Relieve Ayacucho: {len(tiles)} teselas, {GRID}×{GRID} alturas, "
          f"rango {grid.min():.0f}–{grid.max():.0f} m")


if __name__ == "__main__":
    main()
