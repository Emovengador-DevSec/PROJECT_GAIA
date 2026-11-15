"""Cache open Sentinel-2 true-colour scenes for the close view of rural terrain."""
import io
import math
from contextlib import ExitStack
from pathlib import Path

import httpx
import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window, bounds

from .config import load_aois
from .field_evidence import write_json
from .settings import PUBLISHED

STAC = "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items"
SCENES = {"ayacucho-huanta": ("S2A_18LWL_20260920_0_L2A", "S2A_18LXL_20260920_0_L2A")}
DATA_POLICY = "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice"
TILE = 2048


def scene(ident: str) -> dict:
    url = f"{STAC}/{ident}"
    response = httpx.get(url, timeout=20)
    response.raise_for_status()
    item = response.json()
    asset = item["assets"]["visual"]
    if item["id"] != ident or not asset["href"].startswith("https://sentinel-cogs.s3.us-west-2.amazonaws.com/"):
        raise ValueError("Escena Sentinel-2 inesperada")
    return {
        "id": ident, "source_url": url, "asset": asset["href"], "date": item["properties"]["datetime"][:10],
        "cloud_cover_pct": item["properties"]["eo:cloud_cover"],
    }


def publish(aoi):
    scenes = [scene(ident) for ident in SCENES[aoi]]
    west, south, east, north = load_aois()[aoi].bbox
    width = math.ceil((east - west) * 111_320 * math.cos(math.radians((south + north) / 2)) / 10)
    height = math.ceil((north - south) * 111_320 / 10)
    transform = from_bounds(west, south, east, north, width, height)
    output = PUBLISHED / "field-aerial" / aoi
    output.mkdir(parents=True, exist_ok=True)
    tiles = []
    with (
        rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="2"),
        ExitStack() as stack,
    ):
        rasters = []
        for item in scenes:
            source = stack.enter_context(rasterio.open(item["asset"]))
            if source.count < 3 or tuple(source.res) != (10.0, 10.0):
                raise ValueError("La escena no es color natural de 10 m")
            rasters.append(stack.enter_context(WarpedVRT(
                source, crs="EPSG:4326", transform=transform, width=width, height=height, add_alpha=True,
            )))
        for x in range(0, width, TILE):
            for y in range(0, height, TILE):
                window = Window(x, y, min(TILE, width - x), min(TILE, height - y))
                tile = save_tile(output, window, rasters)
                tiles.append({
                    "image_url": f"/api/field-aerial/{aoi}/{tile}", "bounds": bounds(window, transform),
                })
    payload = {
        "source": "Copernicus Sentinel-2 L2A · color natural",
        "license_url": DATA_POLICY, "scenes": scenes, "tiles": tiles, "resolution_m": 10,
        "date": scenes[0]["date"],
    }
    write_json(output / "catalog.json", payload)
    return {"date": payload["date"], "tiles": len(tiles), "scenes": [item["id"] for item in scenes]}


def save_tile(output: Path, window: Window, rasters: list) -> str:
    stack = np.zeros((4, int(window.height), int(window.width)), dtype="uint8")
    for raster in rasters:
        tile = raster.read(window=window)
        if tile.shape[0] != 4:
            raise ValueError("Faltan bandas del mosaico Sentinel-2")
        valid = (tile[3] != 0) & (stack[3] == 0)
        stack[:, valid] = tile[:, valid]
    image = np.moveaxis(stack, 0, -1)
    complete = bool(np.all(stack[3]))
    filename = f"{int(window.col_off)}-{int(window.row_off)}.{'jpg' if complete else 'png'}"
    raster = Image.fromarray(image[:, :, :3] if complete else image)
    with io.BytesIO() as buffer:
        raster.save(buffer, "JPEG" if complete else "PNG", quality=88)
        (output / filename).write_bytes(buffer.getvalue())
    return filename
