"""Agrupa detecciones FIRMS en hexágonos de unos 10 km, conservando sus fechas."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.prepared import prep

RADIUS_M = 5000
LOCAL = "+proj=laea +lat_0=-10 +lon_0=-75 +datum=WGS84 +units=m"
PROJECT = Transformer.from_crs("EPSG:4326", LOCAL, always_xy=True)
UNPROJECT = Transformer.from_crs(LOCAL, "EPSG:4326", always_xy=True)


@lru_cache(maxsize=1)
def _regions():
    path = Path(__file__).resolve().parents[3] / "apps/web/public/globe/peru-boundaries.geojson"
    features = json.loads(path.read_text(encoding="utf-8"))["features"]
    return [(item["properties"]["name"], prep(shape(item["geometry"])))
            for item in features if item["properties"]["level"] == 1]


def region_name(lon: float, lat: float) -> str:
    point = Point(lon, lat)
    return next((name for name, area in _regions() if area.covers(point)), "Perú")


def _axial(x: float, y: float) -> tuple[int, int]:
    q, r = (math.sqrt(3) * x / 3 - y / 3) / RADIUS_M, 2 * y / (3 * RADIUS_M)
    a, b, c = round(q), round(r), round(-q - r)
    errors = (abs(a - q), abs(b - r), abs(c + q + r))
    if errors[0] > max(errors[1:]):
        a = -b - c
    elif errors[1] > errors[2]:
        b = -a - c
    return a, b


def aggregate(features: list[dict]) -> list[dict]:
    cells: dict[tuple[int, int], list[dict]] = {}
    for feature in features:
        p = feature.get("properties", {})
        if p.get("kind") != "fire" or feature.get("geometry", {}).get("type") != "Point":
            continue
        lon, lat = feature["geometry"]["coordinates"][:2]
        if not all(math.isfinite(v) for v in (lon, lat)) or not (-180 <= lon <= 180 and -90 < lat < 90):
            continue
        cell = _axial(*PROJECT.transform(lon, lat))
        cells.setdefault(cell, []).append(feature)
    result = []
    for (q, r), members in cells.items():
        x = RADIUS_M * math.sqrt(3) * (q + r / 2)
        y = RADIUS_M * 1.5 * r
        lon, lat = UNPROJECT.transform(x, y)
        ring = [UNPROJECT.transform(x + RADIUS_M * math.cos(math.radians(60 * i - 30)),
                                    y + RADIUS_M * math.sin(math.radians(60 * i - 30))) for i in range(6)]
        ring.append(ring[0])
        dates = sorted(item["properties"]["date"] for item in members)
        identifier = f"firms-cell-{q}-{r}"
        result.append({
            "type": "Feature", "id": identifier, "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "id": identifier, "kind": "fire", "source": "NASA FIRMS", "source_kind": "complementary",
                "title": f"{len(members)} focos de calor en una celda", "place": region_name(lon, lat),
                "date": dates[-1], "first_date": dates[0],
                "level": "medio", "confidence": "detecciones VIIRS",
                "source_url": "https://firms.modaps.eosdis.nasa.gov/map/", "granules": [],
                "metrics": {"count": len(members)},
                "center": [lon, lat],
                "members": [{"id": item["properties"]["id"], "date": item["properties"]["date"]}
                            for item in members],
                "note": "Celda de unos 10 km. La altura representa el número de focos detectados. "
                        "La extensión de la celda es una agrupación para visualizar observaciones.",
                "exposure": None,
            },
        })
    return result
