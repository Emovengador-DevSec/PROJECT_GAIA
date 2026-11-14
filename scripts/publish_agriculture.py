"""Publish cropland slope classes using original Mapzen tiles and the active HV patches."""
from __future__ import annotations

import json
from contextlib import ExitStack
from datetime import UTC, datetime

import numpy as np
import rasterio
import yaml
from rasterio.merge import merge
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject, transform_bounds

from sarlab_pipeline import settings as S
from sarlab_pipeline.agriculture import FIELDS, SLOPE_THRESHOLD_DEG, slope_degrees, slope_exposure
from sarlab_pipeline.ingest import _write_json, load_catalog

AOI = "ayacucho-huanta"


def publish():
    inputs = [(name, entry) for name, entry in load_catalog()["items"].items()
              if entry.get("source") == "mapzen" and entry.get("zoom") == 12]
    if not inputs:
        raise ValueError("Descarga e ingiere primero las teselas de elevación.")
    with ExitStack() as stack:
        rasters = [stack.enter_context(rasterio.open(S.RAW / entry["path"])) for _, entry in inputs]
        mosaic, affine = merge(rasters)
        bounds = transform_bounds("EPSG:4326", "EPSG:32718", -74.42, -13.42, -73.88, -12.78)
        width, height = int(np.ceil((bounds[2] - bounds[0]) / 30)), int(np.ceil((bounds[3] - bounds[1]) / 30))
        bounds = (bounds[0], bounds[3] - height * 30, bounds[0] + width * 30, bounds[3])
        target_affine = from_bounds(*bounds, width, height)
        elevation = np.full((height, width), np.nan, "float32")
        reproject(mosaic[0], elevation, src_crs=rasters[0].crs, src_transform=affine,
                  src_nodata=-32768, dst_crs="EPSG:32718", dst_transform=target_affine,
                  dst_nodata=np.nan, resampling=Resampling.bilinear)
    folder = S.INTERIM / AOI
    folder.mkdir(parents=True, exist_ok=True)
    slope = folder / "slope-30m.tif"
    with rasterio.open(slope, "w", driver="GTiff", height=height, width=width, count=1,
                       dtype="float32", crs="EPSG:32718", transform=target_affine,
                       nodata=np.nan, compress="deflate") as raster:
        raster.write(slope_degrees(elevation, 30), 1)
    gcov = S.PROCESSED / AOI / "gcov"
    period = json.loads((gcov / "active-comparison.json").read_text())["period"]
    features = json.loads((gcov / period / "alerts_hvhv.geojson").read_text())["features"]
    exposure = json.loads((S.PUBLISHED / "exposure" / f"{AOI}.json").read_text(encoding="utf-8"))
    patches = {}
    for feature in features:
        ident = feature["properties"]["id"]
        target = exposure["alerts"][ident]["cropland_ha"] or 0
        patches[ident] = slope_exposure(feature["geometry"], folder / "worldcover.tif", slope, target)
    result = {"aoi": AOI, "threshold_deg": SLOPE_THRESHOLD_DEG, "grid_m": 30, "period": period,
              "source": "Mapzen Terrain Tiles", "source_url": "https://registry.opendata.aws/terrain-tiles/",
              "attribution_url": "https://github.com/tilezen/joerd/blob/master/docs/attribution.md",
              "retrieved_at": max(entry["ingested_at"] for _, entry in inputs),
              "published_at": datetime.now(UTC).isoformat(),
              "note": "Pendiente geométrica de un DEM compuesto, sobre rejilla UTM de 30 m. "
                      "Cruce ponderado por área con cultivos WorldCover 2021 dentro de manchas HV de 2026. "
                      "No confirma suelo desnudo ni erosión. El corte de 15° es exploratorio.",
              "granules": [name for name, _ in inputs],
              "region": {field: round(sum(row[field] for row in patches.values()), 3) for field in FIELDS},
              **yaml.safe_load((S.CONFIG_DIR / "agriculture.yaml").read_text(encoding="utf-8")),
              "alerts": patches}
    output = S.PUBLISHED / "agriculture"
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / f"{AOI}.json", result)
    print(json.dumps({"patches": len(patches), **result["region"]}))


if __name__ == "__main__":
    publish()
