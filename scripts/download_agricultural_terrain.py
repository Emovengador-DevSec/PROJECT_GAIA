"""Download bounded Mapzen elevation originals for the active Ayacucho study box."""
import math
from concurrent.futures import ThreadPoolExecutor

import httpx

from sarlab_pipeline import settings as S


def main():
    # A margin keeps the slope derivative away from mosaic edges.
    west, south, east, north = (-74.42, -13.42, -73.88, -12.78)
    def tile(lon, lat):
        return int((lon + 180) / 360 * 4096), int(
            (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 4096)
    left, top = tile(west, north)
    right, bottom = tile(east, south)
    tiles = [(x, y) for x in range(left, right + 1) for y in range(top, bottom + 1)]
    if len(tiles) > 100:
        raise ValueError("La descarga debe tener como máximo 100 teselas.")
    S.INBOX.mkdir(parents=True, exist_ok=True)

    def fetch(item):
        x, y = item
        target = S.INBOX / f"MAPZEN_12_{x}_{y}.tif"
        response = httpx.get(f"https://elevation-tiles-prod.s3.amazonaws.com/geotiff/12/{x}/{y}.tif",
                             timeout=45)
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            raise ValueError("La tesela supera 2 MB.")
        target.write_bytes(response.content)
        return len(response.content)
    with ThreadPoolExecutor(max_workers=6) as pool:
        size = sum(pool.map(fetch, tiles))
    print(f"Mapzen: {len(tiles)} originales, {size / 1e6:.2f} MB, listos para sarlab ingest.")


if __name__ == "__main__":
    main()
