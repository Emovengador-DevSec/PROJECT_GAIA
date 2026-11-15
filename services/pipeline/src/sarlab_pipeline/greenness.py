"""Publish quality-filtered NASA MODIS NDVI from the public Planetary Computer mirror."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
from statistics import median

import httpx
import numpy as np
import rasterio
from rasterio.warp import transform

from .config import load_aois
from .field_evidence import write_json
from .settings import DATA_DIR, PUBLISHED

MIRROR = "https://planetarycomputer.microsoft.com"
COLLECTION = "modis-13Q1-061"
SOURCE = "https://doi.org/10.5067/MODIS/MOD13Q1.061"
CONTAINER = "https://modiseuwest.blob.core.windows.net/modis-061-cogs/"
BANDS = ("250m_16_days_NDVI", "250m_16_days_pixel_reliability")
PERIOD = ("10-25", "12-05")
REFERENCE = {"ayacucho-huanta": (-74.2, -13.1)}


def at_point(asset, token, lon, lat):
    url = asset["href"]
    if not url.startswith(CONTAINER) or "?" in url or not url.endswith(".tif"):
        raise ValueError("Archivo MODIS inesperado")
    with rasterio.open(f"{url}?{token}") as raster:
        x, y = transform("EPSG:4326", raster.crs, [lon], [lat])
        sample = next(raster.sample(zip(x, y, strict=True), masked=True))[0]
        return None if np.ma.is_masked(sample) else int(sample)


def yearly(year, client, token, lon, lat, cache):
    path = cache / f"{year}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    box = f"{lon - .00001},{lat - .00001},{lon + .00001},{lat + .00001}"
    start, end = (f"{year}-{day}" for day in PERIOD)
    response = client.get(f"{MIRROR}/api/stac/v1/search", params={
        "collections": COLLECTION, "bbox": box, "limit": 12,
        "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
    })
    response.raise_for_status()
    observations = {}
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="12", GDAL_HTTP_MAX_RETRY="1",
    ):
        for item in response.json()["features"]:
            stamp = item["id"].split(".")[1]
            if not stamp.startswith(f"A{year}"):
                continue
            day = (date(year, 1, 1) + timedelta(days=int(stamp[-3:]) - 1)).isoformat()
            if not start <= day <= end or day in observations:
                continue
            assets = item["assets"]
            if at_point(assets[BANDS[1]], token, lon, lat) != 0:
                continue
            value = at_point(assets[BANDS[0]], token, lon, lat)
            if value is not None and -2000 <= value <= 10_000:
                observations[day] = {"ndvi": round(value * .0001, 4), "scene": item["id"]}
    if len(observations) < 2:
        return None
    result = {
        "year": year, "median": round(median(item["ndvi"] for item in observations.values()), 3),
        "count": len(observations), "months": len({key[5:7] for key in observations}),
        "observations": observations,
    }
    write_json(path, result)
    return result


def publish(aoi):
    west, south, east, north = load_aois()[aoi].bbox
    lon, lat = REFERENCE.get(aoi, ((west + east) / 2, (south + north) / 2))
    cache = DATA_DIR / "catalog" / COLLECTION / aoi / f"{lat:.5f}_{lon:.5f}"
    requested = range(2000, datetime.now(UTC).year + 1)
    with httpx.Client(timeout=18, transport=httpx.HTTPTransport(retries=1)) as client:
        try:
            response = client.get(f"{MIRROR}/api/sas/v1/token/modiseuwest/modis-061-cogs")
            response.raise_for_status()
            token = response.json()["token"]
        except (httpx.HTTPError, KeyError, ValueError):
            raise ValueError("No se pudo abrir el archivo público de MODIS") from None
        years = []
        with ThreadPoolExecutor(max_workers=7) as pool:
            futures = [pool.submit(yearly, year, client, token, lon, lat, cache) for year in requested]
            for future in as_completed(futures):
                try:
                    if result := future.result():
                        years.append(result)
                except (httpx.HTTPError, KeyError, ValueError, rasterio.errors.RasterioError):
                    continue
    if not years:
        raise ValueError("Faltan observaciones MODIS de buena calidad para el píxel de referencia")
    years.sort(key=lambda item: item["year"])
    payload = {
        "product": "NASA MODIS Terra · MOD13Q1 v061", "source_url": SOURCE,
        "archive_url": f"{MIRROR}/api/stac/v1/collections/{COLLECTION}",
        "center": {"latitude": lat, "longitude": lon}, "resolution_m": 250, "years": years,
        "season": "25 de octubre a 5 de diciembre",
        "incomplete_years": sorted(set(requested) - {year["year"] for year in years}),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    write_json(PUBLISHED / "greenness" / f"{aoi}.json", payload)
    return {"years": len(years), "first": years[0]["year"], "last": years[-1]["year"],
            "incomplete_years": payload["incomplete_years"]}
