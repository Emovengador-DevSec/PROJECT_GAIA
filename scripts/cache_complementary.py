"""Prepara recortes públicos de NASA GIBS y del archivo RADARSAT-1."""

import argparse
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx
import numpy as np
import rasterio
import yaml
from rasterio.control import GroundControlPoint
from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.warp import reproject
from rio_tiler.utils import render

from sarlab_pipeline.config import load_aois
from sarlab_pipeline.settings import CONFIG_DIR, PUBLISHED

WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"


def historic_png(client: httpx.Client, layer: dict, bounds: tuple, width: int, height: int) -> bytes:
    metadata = client.get(layer["href"])
    metadata.raise_for_status()
    scene = metadata.json()
    if scene["id"] != layer["scene"] or scene["properties"]["datetime"][:10] != layer["date"]:
        raise ValueError("La escena canadiense no coincide con el identificador y fecha configurados.")
    url = scene["assets"]["cog"]["href"]
    if not url.startswith((
        "https://radarsat-r1-l1-cog.s3.ca-central-1.amazonaws.com/",
        "https://s3-ca-central-1.amazonaws.com/radarsat-r1-l1-cog/",
    )):
        raise ValueError("El GeoTIFF no pertenece al archivo oficial RADARSAT-1.")
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY=1):
        with rasterio.open(url) as src:
            gcps, crs = src.gcps
            if len(gcps) < 4 or crs is None:
                raise ValueError("La escena no tiene suficientes puntos de control geográfico.")
            size = min(2048, src.width, src.height)
            image = src.read(1, out_shape=(size, size), resampling=Resampling.average)
            scaled = [GroundControlPoint(row=g.row * size / src.height, col=g.col * size / src.width,
                                         x=g.x, y=g.y, z=g.z) for g in gcps]
    output = np.zeros((height, width), dtype=np.uint8)
    reproject(image, output, gcps=scaled, src_crs=crs, dst_crs="EPSG:4326", src_nodata=0,
              dst_nodata=0, dst_transform=from_bounds(*bounds, width, height), resampling=Resampling.bilinear)
    return render(output, (output > 0).astype(np.uint8) * 255)


def gibs_png(client: httpx.Client, layer: dict, bounds: tuple, width: int, height: int) -> bytes:
    params = {
        "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap", "SRS": "EPSG:4326",
        "BBOX": ",".join(map(str, bounds)), "WIDTH": width, "HEIGHT": height,
        "FORMAT": "image/png", "TRANSPARENT": "TRUE", "STYLES": "",
        "LAYERS": layer["layer"], "TIME": layer["date"],
    }
    response = client.get(WMS, params=params)
    response.raise_for_status()
    return response.content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aoi")
    parser.add_argument("--layer")
    args = parser.parse_args()
    zones = load_aois()
    config = yaml.safe_load((CONFIG_DIR / "context.yaml").read_text(encoding="utf-8"))
    with httpx.Client(timeout=30) as client:
        for zone, layers in config.items():
            if args.aoi and args.aoi != zone:
                continue
            bounds = zones[zone].bbox
            west, south, east, north = bounds
            width = 768
            height = round(width * (north - south) / (east - west))
            for layer in layers:
                if args.layer and args.layer != layer["id"]:
                    continue
                width = layer.get("width", 768)
                height = round(width * (north - south) / (east - west))
                fetch = historic_png if layer["id"] == "radarsat1" else gibs_png
                for day in [layer["before"], layer["date"]] if "before" in layer else [layer["date"]]:
                    body = fetch(client, {**layer, "date": day}, bounds, width, height)
                    with MemoryFile(body) as image, image.open() as raster:
                        if raster.driver != "PNG" or not raster.dataset_mask().any():
                            print(f"{zone} {layer['id']} {day} sin píxeles visibles")
                            continue
                    target = PUBLISHED / "context" / zone / f"{layer['id']}-{day}.png"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with NamedTemporaryFile(dir=target.parent, delete=False) as handle:
                        tmp = Path(handle.name)
                        handle.write(body)
                    try:
                        tmp.replace(target)
                    finally:
                        tmp.unlink(missing_ok=True)
                    print(f"{zone} {layer['id']} {day}: {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
