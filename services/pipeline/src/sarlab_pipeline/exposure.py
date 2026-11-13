"""Precalcula exposición usando capas locales reales y conserva su procedencia."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import rasterio
from pyproj import CRS, Geod, Transformer
from rasterio.features import geometry_window
from rasterio.mask import mask
from rasterio.warp import transform_geom
from shapely import transform
from shapely.geometry import shape

from . import settings as S
from .config import load_aois

MAX_WINDOW_PIXELS = 10_000_000


def _raster(path: Path, geometry: dict):
    with rasterio.open(path) as src:
        if src.count != 1 or src.crs is None:
            raise ValueError("La capa debe tener una banda y un sistema de referencia definido.")
        projected = transform_geom("EPSG:4326", src.crs, geometry)
        window = geometry_window(src, [projected])
        if window.width * window.height > MAX_WINDOW_PIXELS:
            raise ValueError("La ventana supera 10 millones de píxeles. Recorta la capa a la zona.")
        values, affine = mask(src, [projected], crop=True, filled=False)
        return values[0], affine, CRS.from_wkt(src.crs.to_wkt())


def _population(path: Path, geometry: dict) -> float | None:
    values, _, _ = _raster(path, geometry)
    valid = values.compressed()
    valid = valid[np.isfinite(valid)]
    if not valid.size:
        return None
    if np.any(valid < 0):
        raise ValueError("La población contiene valores negativos sin máscara de nodata.")
    return round(float(valid.sum(dtype="float64")), 1)


def _landcover(path: Path, geometry: dict) -> dict:
    values, affine, crs = _raster(path, geometry)
    if values.count() == 0:
        return {"cropland_ha": None, "forest_ha": None}
    if crs.is_geographic:
        if affine.b or affine.d:
            raise ValueError("El raster geográfico debe tener una rejilla sin rotación.")
        geod = Geod(ellps="WGS84")
        row_areas = []
        for row in range(values.shape[0]):
            west, north = affine * (0, row)
            east, south = affine * (1, row + 1)
            area, _ = geod.polygon_area_perimeter([west, east, east, west], [north, north, south, south])
            row_areas.append(abs(area) / 1e4)
        areas = np.asarray(row_areas)[:, None]
    else:
        factors = [axis.unit_conversion_factor for axis in crs.axis_info[:2]]
        if len(factors) != 2:
            raise ValueError("No se pudo verificar la unidad del sistema de referencia.")
        areas = abs(affine.a * affine.e - affine.b * affine.d) * factors[0] * factors[1] / 1e4
    return {key: round(float(np.sum(np.ma.filled(values == code, False) * areas)), 3)
            for key, code in (("cropland_ha", 40), ("forest_ha", 10))}


def _places(features: list[dict], geometry: dict, buffer_m: float) -> list[str]:
    polygon = shape(geometry)
    center = polygon.centroid
    zone = max(1, min(60, int((center.x + 180) / 6) + 1))
    epsg = (32600 if center.y >= 0 else 32700) + zone
    project = Transformer.from_crs(4326, epsg, always_xy=True).transform
    nearby = transform(polygon, project, interleaved=False).buffer(buffer_m)
    names = []
    for feature in features:
        point = shape(feature["geometry"])
        if nearby.covers(transform(point, project, interleaved=False)):
            names.append(str(feature.get("properties", {}).get("name") or "Centro poblado sin nombre"))
    return names


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
    for name, path, acquired, label, url in (
        ("population", population, population_date, "WorldPop", "https://www.worldpop.org/"),
        ("landcover", landcover, landcover_date, "ESA WorldCover", "https://esa-worldcover.org/"),
        ("places", places, places_date, "OpenStreetMap", "https://www.openstreetmap.org/copyright"),
    ):
        if path is None:
            continue
        if acquired is None:
            raise ValueError(f"Indica la fecha de la fuente con --{name}-date YYYY-MM-DD.")
        date.fromisoformat(acquired)
        if not path.is_file():
            raise ValueError(f"Archivo de {name} no encontrado.")
        sources[name] = {"name": label, "date": acquired, "file": path.name, "url": url}
    if population is not None:
        sources["population"]["unit"] = "people_per_pixel"
    if landcover is not None:
        sources["landcover"]["classes"] = {"40": "Cultivos", "10": "Árboles"}
    settlements = []
    if places is not None:
        if places.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("Recorta el GeoJSON de centros poblados a la zona; máximo 16 MB.")
        collection = json.loads(places.read_text(encoding="utf-8"))
        if collection.get("type") != "FeatureCollection":
            raise ValueError("Los centros poblados deben ser un GeoJSON FeatureCollection.")
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
            metrics = {"population": None, "cropland_ha": None, "forest_ha": None,
                       "settlements": None, "places": None}
            issues = []
            for source, action in (
                ("population", lambda geometry=geometry: {"population": _population(population, geometry)}),
                ("landcover", lambda geometry=geometry: _landcover(landcover, geometry)),
                ("places", lambda geometry=geometry: {"places": _places(settlements, geometry, buffer_m)}),
            ):
                if source not in sources:
                    issues.append(f"Falta la fuente de {source}.")
                    continue
                try:
                    metrics.update(action())
                except (ValueError, rasterio.errors.RasterioError) as exc:
                    issues.append(f"{sources[source]['name']}: {exc}")
            if metrics["places"] is not None:
                metrics["settlements"] = len(metrics["places"])
            alerts[alert_id] = {**metrics, "sources": sources, "issues": issues,
                                "note": "Exposición aproximada sobre el área de cambio; no confirma daños.",
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
