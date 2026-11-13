"""Resumen espacial de tres observaciones diarias GPM IMERG originales."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import xarray as xr

from .. import settings
from ..config import load_aois


def three_day_rain(aoi: str, files: list[Path], variable: str, group: str | None = None) -> dict:
    zones = load_aois()
    if aoi not in zones or len(files) != 3:
        raise ValueError("Selecciona una zona configurada y tres archivos diarios IMERG consecutivos.")
    west, south, east, north = zones[aoi].bbox
    days = []
    paths = []
    for file in files:
        if not file.name.startswith("3B-DAY-") or "3IMERG" not in file.name:
            raise ValueError("Conserva los nombres originales de los productos diarios GPM IMERG.")
        with xr.open_dataset(file, engine="h5netcdf", group=group) as dataset:
            if variable not in dataset:
                raise ValueError("Confirma la variable con sarlab inspect antes de procesar.")
            rain = dataset[variable]
            unit = str(rain.attrs.get("units", "")).lower().replace(" ", "")
            if unit not in ("mm/day", "mmd-1", "mmday-1"):
                raise ValueError("La variable diaria debe expresar precipitación en mm/día.")
            coordinates = {
                role: next((key for key in dataset.variables
                            if dataset[key].attrs.get("standard_name") == role), None)
                for role in ("latitude", "longitude", "time")
            }
            if not all(coordinates.values()):
                raise ValueError("Faltan coordenadas CF de latitud, longitud o tiempo en el grupo.")
            lat, lon, time = (coordinates[key] for key in ("latitude", "longitude", "time"))
            if dataset[time].size != 1 or dataset[lat].ndim != 1 or dataset[lon].ndim != 1:
                raise ValueError("Cada archivo debe tener un día y una rejilla geográfica rectilínea.")
            stamp = str(np.asarray(dataset[time]).ravel()[0])[:10]
            observed = date.fromisoformat(stamp)
            if observed.strftime("%Y%m%d") not in file.name:
                raise ValueError("El tiempo del archivo no coincide con su identificador.")
            lat_index = np.flatnonzero((dataset[lat].values >= south) & (dataset[lat].values <= north))
            lon_index = np.flatnonzero((dataset[lon].values >= west) & (dataset[lon].values <= east))
            subset = rain.isel({
                dataset[lat].dims[0]: lat_index, dataset[lon].dims[0]: lon_index,
            }).squeeze(dataset[time].dims[0], drop=True)
            if subset.size == 0 or subset.size > 1_000_000:
                raise ValueError("La zona debe intersectar una ventana de menos de un millón de píxeles.")
            days.append((observed, subset.load()))
            paths.append(file.name)
    days.sort(key=lambda item: item[0])
    if [item[0] for item in days] != [days[0][0] + timedelta(days=step) for step in range(3)]:
        raise ValueError("Los tres días deben ser consecutivos y distintos.")
    aligned = xr.align(*(item[1] for item in days), join="exact")
    values = np.stack([item.values for item in aligned])
    valid = np.all(np.isfinite(values) & (values >= 0), axis=0)
    cumulative = np.where(valid, values.sum(axis=0), np.nan)
    latitudes = np.asarray(aligned[0][lat])
    shape = [1] * cumulative.ndim
    shape[aligned[0].dims.index(aligned[0][lat].dims[0])] = latitudes.size
    weights = np.broadcast_to(np.cos(np.deg2rad(latitudes)).reshape(shape), cumulative.shape)
    mean = float(np.sum(cumulative[valid] * weights[valid]) / weights[valid].sum()) if valid.any() else None
    result = {
        "aoi_id": aoi, "source": "NASA/GPM · IMERG", "unit": "mm",
        "source_url": "https://gpm.nasa.gov/data/imerg",
        "dates": [item[0].isoformat() for item in days], "granules": sorted(paths),
        "variable": variable, "group": group, "mean_mm": round(mean, 2) if mean is not None else None,
        "valid_area_pct": round(float(valid.mean()) * 100, 2),
        "note": "Acumulado de tres días UTC. Media espacial sobre píxeles válidos en los tres días, "
                "ponderada por área. IMERG estima precipitación en una rejilla de unos 10 km.",
    }
    target = settings.PUBLISHED / "rainfall" / f"{aoi}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
        temp = Path(handle.name)
        json.dump(result, handle, ensure_ascii=False, allow_nan=False)
    try:
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    return result
