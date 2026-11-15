"""Concordancia espacial entre la pérdida de señal NISAR y una fuente independiente."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import rasterio
from pyproj import CRS
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.warp import reproject, transform_geom

from .. import settings
from ..publish.paths import local_cog


def compare_opera(layer_id: str, status: Path, onset: Path, granule: str, observed: str,
                  additional: list[tuple[Path, Path, str, str]] | None = None) -> dict:
    manifest = next(
        (m for path in settings.PROCESSED.glob("*/*/*/manifest_hvhv.json")
         if (m := json.loads(path.read_text(encoding="utf-8")))["id"] == layer_id), None,
    )
    if not manifest or manifest["provenance"].get("product") != "GCOV":
        raise ValueError("Publica una capa NISAR GCOV de cambio HV y selecciona su identificador.")
    first, last = (date.fromisoformat(manifest["dates"][key]) for key in ("a", "b"))
    scenes = [(status, onset, granule, observed), *(additional or [])]
    for status_file, onset_file, scene, acquired in scenes:
        if not scene.startswith("OPERA_L3_DIST-ALERT-HLS_"):
            raise ValueError("Indica el identificador del gránulo OPERA DIST-ALERT-HLS original.")
        if (status_file.name != scene + "_VEG-DIST-STATUS.tif"
                or onset_file.name != scene + "_VEG-DIST-DATE.tif"):
            raise ValueError("Las dos capas OPERA deben provenir del mismo gránulo indicado.")
        parts = scene.split("_")
        if len(parts) < 7 or date.fromisoformat(acquired) < last or acquired.replace("-", "") != parts[4][:8]:
            raise ValueError("La fecha OPERA debe coincidir con el gránulo y alcanzar la última fecha NISAR.")

    raster_path = local_cog(manifest["cog_path"], settings.PROCESSED)
    origin = date(2020, 12, 31)
    with rasterio.open(raster_path) as radar:
        if not radar.crs or not radar.crs.is_projected:
            raise ValueError("La capa NISAR debe usar una rejilla proyectada para medir área.")
        if radar.width * radar.height > 10_000_000:
            raise ValueError("Recorta la capa NISAR a menos de 10 millones de píxeles para el contraste.")
        valid_radar = np.isfinite(radar.read(1, masked=True).filled(np.nan))
        options = dict(dst_transform=radar.transform, dst_crs=radar.crs, resampling=Resampling.nearest)
        classes = np.full(radar.shape, 255, dtype=np.uint8)
        day = np.full(radar.shape, -1, dtype=np.int16)
        for status_file, onset_file, _, _ in sorted(scenes, key=lambda item: item[3]):
            with rasterio.open(status_file) as optical, rasterio.open(onset_file) as dates:
                if (not optical.crs or optical.crs != dates.crs or optical.shape != dates.shape
                        or optical.transform != dates.transform):
                    raise ValueError("Las capas originales de estado y fecha OPERA deben compartir rejilla.")
                scene_classes = np.full(radar.shape, 255, dtype=np.uint8)
                scene_days = np.full(radar.shape, -1, dtype=np.int16)
                reproject(rasterio.band(optical, 1), scene_classes, dst_nodata=255, **options)
                reproject(rasterio.band(dates, 1), scene_days, dst_nodata=-1, **options)
                available = (scene_classes <= 8) & (scene_days >= 0)
                classes[available] = scene_classes[available]
                day[available] = scene_days[available]
        common = valid_radar & (classes <= 8) & (day >= 0)
        opera = np.isin(classes, (3, 6, 7, 8)) & (day > (first - origin).days) & (day <= (last - origin).days)
        alerts = json.loads(raster_path.with_name("alerts_hvhv.geojson").read_text(encoding="utf-8"))
        shapes = [
            transform_geom("EPSG:4326", radar.crs, item["geometry"]) for item in alerts["features"]
            if item.get("geometry") and item["properties"].get("layer_id") == layer_id
        ]
        loss = np.zeros(radar.shape, dtype=bool)
        if shapes:
            loss = rasterize(
                shapes, out_shape=radar.shape, transform=radar.transform, dtype="uint8",
            ).astype(bool)
        axes = CRS.from_user_input(radar.crs).axis_info[:2]
        cell_ha = abs(radar.transform.a * radar.transform.e - radar.transform.b * radar.transform.d)
        cell_ha *= axes[0].unit_conversion_factor * axes[1].unit_conversion_factor / 10_000

    total_radar = int(np.count_nonzero(loss & common))
    total_opera = int(np.count_nonzero(opera & common))
    overlap = int(np.count_nonzero(loss & opera & common))
    union = total_radar + total_opera - overlap
    count_common = int(common.sum())
    result = {
        "layer_id": layer_id, "source": "OPERA DIST-ALERT-HLS · NASA/JPL",
        "granule": granule, "date": max(item[3] for item in scenes), "dates": manifest["dates"],
        "granules": [{"name": item[2], "date": item[3]} for item in scenes],
        "source_url": "https://doi.org/10.5067/SNWG/OPERA_L3_DIST-ALERT-HLS_V1.001",
        "status": "ok" if count_common and union else "insufficient",
        "common_ha": round(count_common * cell_ha, 2), "nisar_loss_ha": round(total_radar * cell_ha, 2),
        "opera_disturbance_ha": round(total_opera * cell_ha, 2), "overlap_ha": round(overlap * cell_ha, 2),
        "agreement_pct": round(100 * overlap / union, 2) if union else None,
        "nisar_confirmed_pct": round(100 * overlap / total_radar, 2) if total_radar else None,
        "radar_coverage_pct": round(100 * count_common / valid_radar.sum(), 2) if valid_radar.any() else 0,
        "note": ("Intersección dividida por unión dentro de la cobertura común. "
                 "La concordancia compara señales y requiere evidencia adicional para atribuir un incendio."),
    }
    target = settings.PUBLISHED / "validation" / f"{layer_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
        temp = Path(handle.name)
        json.dump(result, handle, ensure_ascii=False, allow_nan=False)
    try:
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    return result
