"""Precalcula exposición usando capas locales reales y conserva su procedencia."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

import numpy as np
import rasterio
from pyproj import CRS, Geod, Transformer
from rasterio.features import geometry_window
from rasterio.mask import mask
from rasterio.warp import transform_geom
from shapely import area, box, distance, intersection, orient_polygons, points, transform
from shapely.geometry import shape

from . import settings as S
from .config import load_aois

MAX_WINDOW_PIXELS = 10_000_000
LANDCOVER_CLASSES = {"cropland_ha": 40, "forest_ha": 10, "grassland_ha": 30}
LANDCOVER_AREA_KEYS = (*LANDCOVER_CLASSES, "other_landcover_ha", "landcover_unmapped_ha")
WGS84 = Geod(ellps="WGS84")


def _raster(path: Path, geometry: dict):
    with rasterio.open(path) as src:
        if src.count != 1 or src.crs is None:
            raise ValueError("La capa debe tener una banda y un sistema de referencia definido.")
        projected = transform_geom("EPSG:4326", src.crs, geometry)
        window = geometry_window(src, [projected])
        if window.width * window.height > MAX_WINDOW_PIXELS:
            raise ValueError("La ventana supera 10 millones de píxeles. Recorta la capa a la zona.")
        values, affine = mask(src, [projected], crop=True, filled=False, all_touched=True)
        if affine.b or affine.d or affine.a <= 0 or affine.e >= 0:
            raise ValueError("La capa de exposición requiere una rejilla norte-arriba sin rotación.")
        return values[0], affine, CRS.from_wkt(src.crs.to_wkt()), shape(projected)


def _weighted_cells(path: Path, geometry: dict, *, with_columns: bool = False):
    """Weight each valid cell by the fraction of its footprint inside the alert."""
    pixels, affine, crs, polygon = _raster(path, geometry)
    valid = ~np.ma.getmaskarray(pixels) & np.isfinite(pixels.data)
    rows, cols = np.nonzero(valid)
    weights = np.empty(len(rows), dtype="float64")
    for start in range(0, len(rows), 10_000):
        section = slice(start, start + 10_000)
        left = affine.c + affine.a * cols[section]
        top = affine.f + affine.e * rows[section]
        cells = box(left, top + affine.e, left + affine.a, top)
        weights[section] = area(intersection(cells, polygon)) / abs(affine.a * affine.e)
    result = (pixels.data[rows, cols], weights.clip(0, 1), rows, affine, crs, polygon)
    return (*result, cols) if with_columns else result


def _population(path: Path, geometry: dict) -> float | None:
    values, weights, *_ = _weighted_cells(path, geometry)
    if not weights.any():
        return None
    if np.any(values < 0):
        raise ValueError("La población contiene valores negativos sin máscara de nodata.")
    return round(float(np.dot(values, weights)), 1)


def _landcover(path: Path, geometry: dict) -> dict:
    values, weights, rows, affine, crs, polygon = _weighted_cells(path, geometry)
    if crs.is_geographic:
        if crs.to_epsg() != 4326:
            raise ValueError("La rejilla geográfica de cobertura debe estar en EPSG:4326.")
        row_areas = []
        distinct_rows, indices = np.unique(rows, return_inverse=True)
        for row in distinct_rows:
            west, north = affine * (0, row)
            east, south = affine * (1, row + 1)
            area_m2, _ = WGS84.polygon_area_perimeter([west, east, east, west], [north, north, south, south])
            row_areas.append(abs(area_m2) / 1e4)
        cell_areas = np.asarray(row_areas)[indices] * weights
        total_area = abs(WGS84.geometry_area_perimeter(orient_polygons(polygon))[0]) / 1e4
    else:
        factors = [axis.unit_conversion_factor for axis in crs.axis_info[:2]]
        if len(factors) != 2:
            raise ValueError("No se pudo verificar la unidad del sistema de referencia.")
        area_factor = factors[0] * factors[1] / 1e4
        cell_areas = abs(affine.a * affine.e) * area_factor * weights
        total_area = polygon.area * area_factor
    mapped = float(cell_areas.sum())
    if not total_area or not mapped:
        return {**dict.fromkeys(LANDCOVER_CLASSES), "other_landcover_ha": None,
                "landcover_unmapped_ha": round(total_area, 3), "landcover_coverage_pct": 0.0}
    other = float(cell_areas[~np.isin(values, list(LANDCOVER_CLASSES.values()))].sum())
    classes = {key: round(float(cell_areas[values == code].sum()), 3)
               for key, code in LANDCOVER_CLASSES.items()}
    return {**classes, "other_landcover_ha": round(other, 3),
            "landcover_unmapped_ha": round(max(0, total_area - mapped), 3),
            "landcover_coverage_pct": round(min(100, 100 * mapped / total_area), 1)}


def _places(features: list[dict], geometry: dict, buffer_m: float) -> list[dict]:
    if not features:
        return []
    polygon = shape(geometry)
    center = polygon.centroid
    zone = max(1, min(60, int((center.x + 180) / 6) + 1))
    epsg = (32600 if center.y >= 0 else 32700) + zone
    project = Transformer.from_crs(4326, epsg, always_xy=True).transform
    projected = transform(polygon, project, interleaved=False)
    coordinates = np.array([feature["geometry"]["coordinates"][:2] for feature in features])
    projected_points = transform(points(coordinates), project, interleaved=False)
    distances = distance(projected, projected_points)
    nearby = []
    for index in np.flatnonzero(distances <= buffer_m):
        properties = features[index].get("properties", {})
        place = {"name": str(properties.get("name") or "Centro poblado sin nombre"),
                 "distance_m": round(float(distances[index]))}
        node_id = properties.get("osm_id")
        if isinstance(node_id, int) and node_id > 0:
            place["url"] = f"https://www.openstreetmap.org/node/{node_id}"
        nearby.append(place)
    return sorted(nearby, key=lambda item: (item["distance_m"], item["name"]))


def _source_url(path: Path) -> str | None:
    with rasterio.open(path) as src:
        value = src.tags().get("source", "")
    url = urlsplit(value)
    hosts = {"data.worldpop.org", "esa-worldcover.s3.eu-central-1.amazonaws.com"}
    if url.scheme == "https" and url.netloc in hosts and not (url.query or url.fragment):
        return value
    return None


def calculate(aoi_id: str, population: Path | None = None, landcover: Path | None = None,
              places: Path | None = None, population_unit: str | None = None,
              population_date: str | None = None, landcover_date: str | None = None,
              places_date: str | None = None, buffer_m: float = 2000) -> dict:
    """Suma personas por píxel, calcula hectáreas y cuenta asentamientos cercanos.

    WorldPop debe declarar personas por píxel. Las densidades necesitan otra conversión.
    Los polígonos representan exposición territorial, no personas afectadas confirmadas.
    """
    if aoi_id not in load_aois():
        raise ValueError("Zona no configurada.")
    if population is not None and population_unit != "people_per_pixel":
        raise ValueError("Confirma --population-unit people_per_pixel para el raster de WorldPop.")
    if not 0 <= buffer_m <= 10_000:
        raise ValueError("El radio debe estar entre 0 y 10000 m.")
    sources = {}
    cc_by = "https://creativecommons.org/licenses/by/4.0/"
    for name, path, acquired, label, url, license_id, license_url in (
        ("population", population, population_date, "WorldPop", "https://www.worldpop.org/",
         "CC BY 4.0", cc_by),
        ("landcover", landcover, landcover_date, "ESA WorldCover", "https://esa-worldcover.org/",
         "CC BY 4.0", cc_by),
        ("places", places, places_date, "© OpenStreetMap contributors", "https://www.openstreetmap.org/copyright",
         "ODbL 1.0", "https://opendatacommons.org/licenses/odbl/1-0/"),
    ):
        if path is None:
            continue
        if acquired is None:
            raise ValueError(f"Indica la fecha de la fuente con --{name}-date YYYY-MM-DD.")
        year = date.fromisoformat(acquired).year
        if not path.is_file():
            raise ValueError(f"Archivo de {name} no encontrado.")
        if name != "places":
            url = _source_url(path) or url
        sources[name] = {"name": label, "date": acquired, "year": year, "file": path.name, "url": url,
                         "license": license_id, "license_url": license_url}
    if population is not None:
        sources["population"]["unit"] = "people_per_pixel"
        sources["population"]["attribution"] = "WorldPop, University of Southampton"
    if landcover is not None:
        sources["landcover"]["classes"] = {"40": "Cultivos", "10": "Árboles", "30": "Pastizal"}
        sources["landcover"]["attribution"] = (
            f"© ESA WorldCover project {sources['landcover']['year']}. "
            "Contains modified Copernicus Sentinel data processed by ESA WorldCover consortium."
        )
    settlements = []
    if places is not None:
        if places.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("Recorta el GeoJSON de centros poblados a la zona; máximo 16 MB.")
        collection = json.loads(places.read_text(encoding="utf-8"))
        if collection.get("type") != "FeatureCollection":
            raise ValueError("Los centros poblados deben ser un GeoJSON FeatureCollection.")
        sources["places"]["source_bbox"] = collection.get("bbox")
        sources["places"]["retrieved_at"] = collection.get("retrieved_at")
        settlements = collection.get("features", [])
        only_points = all(f.get("geometry", {}).get("type") == "Point" for f in settlements)
        if len(settlements) > 100_000 or not only_points:
            raise ValueError("Se admiten hasta 100000 centros poblados de tipo Point en EPSG:4326.")
        for settlement in settlements:
            coordinates = settlement["geometry"].get("coordinates", [])
            if (len(coordinates) < 2 or not all(isinstance(c, (int, float)) for c in coordinates[:2])
                    or not -180 <= coordinates[0] <= 180 or not -90 <= coordinates[1] <= 90):
                raise ValueError("Cada centro poblado debe tener coordenadas lon/lat válidas en EPSG:4326.")
    alerts = {}
    for path in sorted((S.PROCESSED / aoi_id).glob("*/*/alerts*.geojson")):
        collection = json.loads(path.read_text(encoding="utf-8"))
        for feature in collection.get("features", []):
            props = feature.get("properties", {})
            alert_id = props.get("id")
            if not alert_id:
                continue
            geometry = feature["geometry"]
            epsg = collection.get("crs_epsg", props.get("epsg", 4326))
            if epsg != 4326:
                geometry = transform_geom(f"EPSG:{epsg}", "EPSG:4326", geometry)
            metrics = {**dict.fromkeys(LANDCOVER_AREA_KEYS), "landcover_coverage_pct": None,
                       "population": None, "settlements": None, "places": None, "nearby_places": None}
            issues = []
            for source, action in (
                ("population", lambda geometry=geometry: {"population": _population(population, geometry)}),
                ("landcover", lambda geometry=geometry: _landcover(landcover, geometry)),
                ("places", lambda geometry=geometry:
                    {"nearby_places": _places(settlements, geometry, buffer_m)}),
            ):
                if source not in sources:
                    issues.append(f"Falta la fuente de {source}.")
                    continue
                try:
                    estimates = action()
                    if source == "population" and estimates["population"] is None:
                        issues.append("WorldPop no tiene píxeles válidos dentro de la mancha.")
                    metrics.update(estimates)
                except (ValueError, rasterio.errors.RasterioError) as exc:
                    issues.append(f"{sources[source]['name']}: {exc}")
            if metrics["nearby_places"] is not None:
                metrics["places"] = [place["name"] for place in metrics["nearby_places"]]
                metrics["settlements"] = len(metrics["nearby_places"])
            alerts[alert_id] = {**metrics, "sources": sources, "issues": issues,
                                "note": "Estimación dentro del área de cambio. La población se pondera por "
                                        "la fracción de cada píxel. Requiere validación en campo.",
                                "settlement_buffer_m": buffer_m}
    result = {"aoi_id": aoi_id, "generated_at": datetime.now(UTC).isoformat(),
              "sources": sources, "alerts": alerts}
    output = S.PUBLISHED / "exposure" / f"{aoi_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                            prefix=f".{aoi_id}-", suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(result, handle, ensure_ascii=False, indent=2)
    try:
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return result
