"""Georeferenced NASA GIBS imagery with recorded requests and per-polygon outlines.

No legacy PNG is assigned a geographic transform by guessing. This publisher fetches
new, explicitly bounded images and archives the exact WMS request and scene metadata.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from io import BytesIO

import httpx
import numpy as np
import yaml
from PIL import Image, ImageDraw
from pyproj import CRS, Transformer
from shapely import transform
from shapely.geometry import box, shape

from .photos import USER_AGENT, Collector
from .settings import CONFIG_DIR, PUBLISHED

WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"


def crop_bounds(geometry: dict, buffer_m: float = 300) -> tuple[float, float, float, float]:
    polygon = shape(geometry)
    center = polygon.centroid
    local = CRS.from_proj4(f"+proj=aeqd +lat_0={center.y} +lon_0={center.x} +datum=WGS84 +units=m")
    forward = Transformer.from_crs(4326, local, always_xy=True).transform
    backward = Transformer.from_crs(local, 4326, always_xy=True).transform
    return transform(
        transform(polygon, forward, interleaved=False).buffer(buffer_m), backward, interleaved=False
    ).bounds


def outlined_crop(
    image: Image.Image, bounds: list | tuple, geometry: dict, *, outline: bool = True
) -> tuple[Image.Image, list]:
    west, south, east, north = bounds
    if west >= east or south >= north:
        raise ValueError("Extensión geográfica inválida")
    target = crop_bounds(geometry)
    if not box(*bounds).covers(box(*target)):
        raise ValueError("El recorte sale de la imagen georreferenciada")

    def pixel(lon, lat):
        return (lon - west) / (east - west) * image.width, (north - lat) / (north - south) * image.height

    x0, y0 = pixel(target[0], target[3])
    x1, y1 = pixel(target[2], target[1])
    rect = (
        max(0, math.floor(x0)),
        max(0, math.floor(y0)),
        min(image.width, math.ceil(x1)),
        min(image.height, math.ceil(y1)),
    )
    cropped = image.crop(rect).convert("RGBA")
    if cropped.width < 4 or cropped.height < 4:
        raise ValueError("Resolución insuficiente")
    draw = ImageDraw.Draw(cropped)
    polygons = [shape(geometry)] if geometry["type"] == "Polygon" else list(shape(geometry).geoms)
    for polygon in polygons:
        for ring in [polygon.exterior, *polygon.interiors]:
            points = [
                (pixel(lon, lat)[0] - rect[0], pixel(lon, lat)[1] - rect[1]) for lon, lat in ring.coords
            ]
            if outline:
                draw.line(points, fill=(0, 0, 0, 255), width=4)
                draw.line(points, fill=(255, 211, 64, 255), width=2)
    # These are the real bounds of the snapped pixel window, not just the requested buffer.
    snapped = [
        west + rect[0] / image.width * (east - west),
        north - rect[3] / image.height * (north - south),
        west + rect[2] / image.width * (east - west),
        north - rect[1] / image.height * (north - south),
    ]
    return cropped, snapped


def usable_pixels(image: Image.Image) -> bool:
    pixels = np.asarray(image.convert("RGBA"))
    return bool(np.mean(pixels[:, :, 3] > 0) > 0.8 and np.max(np.std(pixels[:, :, :3], axis=(0, 1))) > 2)


def historic_scene(collector: Collector, bounds: list | tuple, search_bounds=None) -> dict | None:
    """Earliest low-cloud archive granule; cloud-free pixels are not asserted."""
    data = collector.get_json(
        CMR,
        {
            "short_name": "HLSL30",
            "version": "2.0",
            "temporal": "2016-01-01T00:00:00Z,2018-12-31T23:59:59Z",
            "bounding_box": ",".join(map(str, search_bounds or bounds)),
            "cloud_cover": "0,5",
            "sort_key": "start_date",
            "page_size": 200,
        },
    )
    for item in data.get("feed", {}).get("entry", []):
        if item.get("cloud_cover") is None or float(item["cloud_cover"]) > 5:
            continue
        footprints = []
        for group in item.get("polygons", []):
            for polygon in group:
                numbers = list(map(float, polygon.split()))
                footprints.append(
                    {
                        "type": "Polygon",
                        "coordinates": [[(numbers[i + 1], numbers[i]) for i in range(0, len(numbers), 2)]],
                    }
                )
        if not any(shape(p).covers(box(*bounds)) for p in footprints):
            continue
        # The query filters cloud cover, but preserve the granule as supporting evidence.
        return {
            "date": item["time_start"][:10],
            "scene": item["producer_granule_id"],
            "cmr_id": item["id"],
            "cloud_cover_pct": float(item["cloud_cover"]),
            "metadata_url": f"https://cmr.earthdata.nasa.gov/search/concepts/{item['id']}.umm_json",
        }
    return None


def publish(aoi: str, *, zone_id: str | None = None) -> dict:
    if not re.fullmatch(r"[a-z0-9-]+", aoi):
        raise ValueError("Identificador de territorio inválido")
    source = PUBLISHED / "remediation" / f"{aoi}.json"
    if not source.exists():
        raise ValueError("Publica primero la remediación del territorio")
    zones = json.loads(source.read_text(encoding="utf-8"))["alerts"]
    if zone_id:
        zones = [zone for zone in zones if zone["alert_id"] == zone_id]
        if not zones:
            raise ValueError("Mancha no encontrada")
    root = PUBLISHED / "place-imagery" / aoi
    root.mkdir(parents=True, exist_ok=True)
    output = root / "catalog.json"
    catalog = (
        json.loads(output.read_text(encoding="utf-8")) if output.exists() else {"aoi_id": aoi, "zones": {}}
    )
    optical = next(
        (
            item
            for item in yaml.safe_load((CONFIG_DIR / "context.yaml").read_text(encoding="utf-8")).get(aoi, [])
            if item["id"] == "hls-optical"
        ),
        None,
    )
    groups = {}
    for zone in zones:
        center = shape(zone["geometry"]).centroid
        key = (math.floor(center.x / 0.05), math.floor(center.y / 0.05))
        groups.setdefault(key, []).append(zone)
    published, missing = 0, 0
    with httpx.Client(timeout=45, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        collector = Collector(root, client)
        search_bounds = [
            min(shape(z["geometry"]).bounds[0] for z in zones),
            min(shape(z["geometry"]).bounds[1] for z in zones),
            max(shape(z["geometry"]).bounds[2] for z in zones),
            max(shape(z["geometry"]).bounds[3] for z in zones),
        ]
        for members in groups.values():
            targets = [crop_bounds(z["geometry"]) for z in members]
            bounds = [
                min(b[0] for b in targets),
                min(b[1] for b in targets),
                max(b[2] for b in targets),
                max(b[3] for b in targets),
            ]
            latitude = (bounds[1] + bounds[3]) / 2
            width = math.ceil((bounds[2] - bounds[0]) * 111320 * math.cos(math.radians(latitude)) / 30)
            height = math.ceil((bounds[3] - bounds[1]) * 110574 / 30)
            if max(width, height) > 4096:
                raise ValueError("Grupo demasiado grande para un recorte de 30 m")
            past = historic_scene(collector, bounds, search_bounds)
            moments = [
                ("past", past["date"] if past else None, "HLS_L30_Nadir_BRDF_Adjusted_Reflectance", past)
            ]
            moments += [
                (
                    moment,
                    optical.get(date_key) if optical else None,
                    optical["layer"] if optical else "",
                    None,
                )
                for moment, date_key in [("before", "before"), ("after", "date")]
            ]
            for moment, day, layer, scene in moments:
                reason = (
                    "Sin escena histórica de 2016–2018 con cobertura completa y ≤ 5 % de nubes "
                    "en el catálogo consultado"
                )
                image = None
                request = None
                if day:
                    params = {
                        "SERVICE": "WMS",
                        "VERSION": "1.1.1",
                        "REQUEST": "GetMap",
                        "SRS": "EPSG:4326",
                        "BBOX": ",".join(map(str, bounds)),
                        "WIDTH": width,
                        "HEIGHT": height,
                        "FORMAT": "image/png",
                        "TRANSPARENT": "TRUE",
                        "STYLES": "",
                        "LAYERS": layer,
                        "TIME": day,
                    }
                    request = str(httpx.Request("GET", WMS, params=params).url)
                    digest = hashlib.sha256(request.encode()).hexdigest()
                    cache = root / "cache" / f"{digest}.png"
                    try:
                        if not cache.exists():
                            response = client.get(WMS, params=params)
                            response.raise_for_status()
                            body = response.content
                            if len(body) > 30_000_000:
                                raise ValueError("Respuesta demasiado grande")
                            candidate = Image.open(BytesIO(body)).convert("RGBA")
                            if candidate.size != (width, height):
                                raise ValueError("Dimensiones distintas de la solicitud")
                            candidate.save(cache)
                            cache.with_suffix(".json").write_text(
                                json.dumps(
                                    {
                                        "request": request,
                                        "crs": "EPSG:4326",
                                        "bounds": bounds,
                                        "width": width,
                                        "height": height,
                                        "retrieved_at": datetime.now(UTC).isoformat(),
                                    }
                                ),
                                encoding="utf-8",
                            )
                        image = Image.open(cache).convert("RGBA")
                        reason = (
                            "La imagen no aporta cobertura óptica suficiente; no se publica un recorte vacío"
                        )
                    except (httpx.HTTPError, OSError, ValueError):
                        reason = (
                            "No se pudo descargar y verificar la imagen de NASA GIBS; "
                            "reintenta sarlab place-imagery"
                        )
                for zone in members:
                    result = {
                        "available": False,
                        "reason": reason,
                        "date": day,
                        "source": "NASA HLS / GIBS · complementario",
                    }
                    if image:
                        raw_crop, _ = outlined_crop(image, bounds, zone["geometry"], outline=False)
                        if usable_pixels(raw_crop):
                            crop, snapped = outlined_crop(image, bounds, zone["geometry"])
                            folder = root / zone["alert_id"]
                            folder.mkdir(exist_ok=True)
                            crop.save(folder / f"{moment}.png")
                            result = {
                                "available": True,
                                "date": day,
                                "bounds": snapped,
                                "crs": "EPSG:4326",
                                "width": crop.width,
                                "height": crop.height,
                                "resolution_m": 30,
                                "layer": layer,
                                "source": "NASA HLS / GIBS · complementario",
                                "author": "NASA / USGS / Copernicus",
                                "source_url": request,
                                "scene": scene["scene"] if scene else None,
                                "scenes": [
                                    s
                                    for s in optical.get("scenes", [])
                                    if datetime.fromisoformat(day).strftime(".%Y%j") in s
                                ]
                                if optical and not scene
                                else [],
                                "scene_metadata": scene,
                                "license": "NASA Earthdata data use policy",
                                "license_url": (
                                    "https://www.earthdata.nasa.gov/engage/open-data-services-and-software/"
                                    "data-use-policy"
                                ),
                                "note": (
                                    "Contorno amarillo: mancha NISAR. Visualización HLS de 30 m; "
                                    "no mide recuperación ni confirma la causa. Nubes pueden ocultar terreno."
                                ),
                                "image_url": (
                                    f"/api/remediation/{aoi}/{zone['alert_id']}/imagery/{moment}.png"
                                ),
                            }
                            published += 1
                    if not result["available"]:
                        missing += 1
                    catalog["zones"].setdefault(zone["alert_id"], {})[moment] = result
            output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    catalog["generated_at"] = datetime.now(UTC).isoformat()
    output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"zones": len(zones), "images": published, "missing": missing, "warnings": collector.errors}
