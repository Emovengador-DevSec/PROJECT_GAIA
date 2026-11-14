"""Flujo principal del MVP: cambio de retrodispersión entre dos fechas sobre una zona."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import settings as S
from .config import load_aois, load_thresholds
from .detection.change import polygons, robust_threshold
from .processing.backscatter import boxcar, diff_db, to_db
from .publish import manifest as M
from .publish.cog import write_cog
from .readers import gcov


def _align(a: gcov.Window, b: gcov.Window) -> tuple[np.ndarray, np.ndarray, gcov.Window]:
    """Recorta ambas ventanas a su intersección común (misma rejilla y EPSG requeridos)."""
    if a.epsg != b.epsg:
        raise ValueError("Las dos fechas tienen EPSG distinto: usa gránulos del mismo track/frame.")
    xs = np.intersect1d(np.round(a.x, 3), np.round(b.x, 3))
    ys = np.intersect1d(np.round(a.y, 3), np.round(b.y, 3))[::-1]
    if xs.size < 2 or ys.size < 2:
        raise ValueError("Las rejillas no se solapan lo suficiente.")
    def cut(w):
        xi = np.isin(np.round(w.x, 3), xs); yi = np.isin(np.round(w.y, 3), ys)
        return w.data[np.ix_(yi, xi)]
    ref = gcov.Window(data=cut(a), x=xs, y=ys, epsg=a.epsg, layer=a.layer, source=a.source)
    return cut(a), cut(b), ref


def change_multi(aoi_id: str, before: Path, after: Path,
                 layers: tuple[str, ...] = ("HHHH", "HVHV"), freq: str = "frequencyA") -> dict:
    """Cambio en varias polarizaciones + resumen comparativo (lo pide el reto)."""
    from .analysis import polarization_summary
    from .readers.gcov import list_layers
    gcov.validate_sequence([before, after])
    available = set(list_layers(before, freq)) & set(list_layers(after, freq))
    if not available.intersection(layers):
        raise ValueError("Las fechas no comparten ninguna polarización solicitada. Revisa sarlab inspect.")
    results = {lay: change_between(aoi_id, before, after, lay, freq=freq)
               for lay in layers if lay in available}
    summary = polarization_summary(results)
    out = Path(next(iter(results.values()))["out_dir"]) if results else None
    if out:
        (out / "polarizations.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"by_layer": {k: {kk: vv for kk, vv in v.items() if kk != "manifest"} for k, v in results.items()},
            "summary": summary}


def change_between(aoi_id: str, before: Path, after: Path, layer: str = "HVHV",
                   speckle: int = 3, freq: str = "frequencyA") -> dict:
    from rasterio.warp import transform_bounds, transform_geom

    gcov.validate_sequence([before, after])
    if _date(before.name) >= _date(after.name):
        raise ValueError("La observación anterior debe preceder a la posterior.")
    aoi = load_aois()[aoi_id]
    thr = load_thresholds()
    epsg = gcov.product_epsg(before, freq)
    bbox = gcov.bbox_to_product_crs(aoi.bbox, epsg)
    wa = gcov.read_window(before, layer, bbox, freq)
    wb = gcov.read_window(after, layer, bbox, freq)
    a, b, ref = _align(wa, wb)
    inside, study_area_m2 = gcov.study_area_mask(ref, aoi.bbox)
    common = inside & np.isfinite(a) & (a > 0) & np.isfinite(b) & (b > 0)
    if not common.any():
        raise ValueError("Las dos fechas no comparten píxeles válidos dentro de la zona.")
    a = np.where(common, a, np.nan)
    b = np.where(common, b, np.nan)
    a_db, b_db = boxcar(to_db(a), speckle), boxcar(to_db(b), speckle)
    a_db[~common] = np.nan
    b_db[~common] = np.nan
    d = diff_db(a_db, b_db)
    res = robust_threshold(d, thr.change_k_sigma)

    tag = f"{_date(wa.source)}__{_date(wb.source)}"
    out = S.PROCESSED / aoi_id / "gcov" / tag
    lid = f"lyr_{aoi_id}_gcov_diff-{layer.lower()}_{tag}"
    cog = write_cog(out / f"diff_{layer.lower()}_db.tif", d, ref.transform, epsg)
    before_cog = write_cog(out / f"before_{layer.lower()}_db.tif", a_db, ref.transform, epsg)
    after_cog = write_cog(out / f"after_{layer.lower()}_db.tif", b_db, ref.transform, epsg)
    man = M.build(lid, "backscatter_diff_db", f"Cambio de retrodispersión {layer[:2]}", "dB", "RdBu",
                  d, cog, aoi_id, {"a": _date(wa.source), "b": _date(wb.source)},
                  [wa.source, wb.source],
                  extra={"product": "GCOV", "layer": layer, "frequency": freq, "epsg": epsg,
                         "threshold_db": res.threshold_db, "median_change_db": res.median,
                         "method": "robust_mad_k_sigma",
                         "mask": "GCOV subswath válido en ambas fechas, recortado al área de estudio"})
    pixel_area_m2 = abs(ref.transform.a * ref.transform.e)
    man["quality"]["valid_area_pct"] = round(min(100., 100 * common.sum() * pixel_area_m2 / study_area_m2), 2)
    rows = np.flatnonzero(common.any(axis=1))
    cols = np.flatnonzero(common.any(axis=0))
    left, top = ref.transform @ (cols[0], rows[0])
    right, bottom = ref.transform @ (cols[-1] + 1, rows[-1] + 1)
    man["coverage_bbox"] = transform_bounds(f"EPSG:{epsg}", "EPSG:4326", left, bottom, right, top)
    observations = np.concatenate((a_db[np.isfinite(a_db)], b_db[np.isfinite(b_db)]))
    low, high = np.percentile(observations, (2, 98))
    if high <= low:
        low, high = float(low) - .5, float(high) + .5
    man["comparison"] = {"before_cog_path": str(before_cog), "after_cog_path": str(after_cog),
                         "range": {"min": float(low), "max": float(high)}}
    alerts = polygons(res.loss, ref.transform, thr.min_alert_pixels)
    px_area_ha = abs(ref.transform.a * ref.transform.e) / 1e4
    for i, f in enumerate(alerts):
        rings = f["geometry"]["coordinates"]
        # Raster-derived polygon rings preserve the exact projected pixel area, including holes.
        ring_areas = [abs(sum(x1 * y2 - x2 * y1
                              for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False))) / 2
                      for ring in rings]
        area_ha = (ring_areas[0] - sum(ring_areas[1:])) / 1e4
        f["geometry"] = transform_geom(f"EPSG:{epsg}", "EPSG:4326", f["geometry"])
        f["properties"] = {"id": f"alr_{aoi_id}_{tag}_{layer.lower()}_{i:03d}",
                           "phenomenon": "backscatter_loss",
                           "source": "NISAR", "provisional": man["quality"]["provisional"],
                           "confidence": "por_validar", "source_epsg": epsg, "epsg": 4326,
                           "aoi_id": aoi_id, "place": aoi.name,
                           "area_ha": round(area_ha, 3),
                           "loss_pixels": round(area_ha / px_area_ha),
                           "granules": man["provenance"]["granules"],
                           "threshold_db": res.threshold_db,
                           "layer_id": lid, "method": "robust_mad_k_sigma",
                           "date_range": [man["dates"]["a"], man["dates"]["b"]]}
    (out / f"alerts_{layer.lower()}.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "crs_epsg": 4326, "features": alerts}), encoding="utf-8")
    man["change_summary"] = {
        "loss_area_ha": round(float(res.loss.sum()) * px_area_ha, 2),
        "mapped_loss_area_ha": round(sum(f["properties"]["area_ha"] for f in alerts), 2),
        "alerts": len(alerts),
    }
    M.write(man, out / f"manifest_{layer.lower()}.json")
    return {"manifest": man, "alerts": len(alerts),
            "mapped_loss_area_ha": man["change_summary"]["mapped_loss_area_ha"],
            "loss_area_ha": man["change_summary"]["loss_area_ha"], "out_dir": str(out)}


def _date(name: str) -> str:
    import re
    m = re.search(r"_(\d{8})T\d{6}_", name)
    return f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}" if m else "unknown"


def run_remediation(aoi_id: str, *, offline: bool = False) -> dict:
    """Compute weighted risk index and NbS recipes for all HV alert polygons.

    Reads the active alerts_hvhv.geojson, enriches each polygon with:
    - Soil data (SoilGrids REST, unless --offline)
    - Slope from agriculture.py D1 output
    - Live fires from FIRMS cache
    - Earthquakes from USGS cache
    - 7-day rainfall from published rainfall data

    Outputs data/04_published/remediation/<aoi_id>.json
    """
    import logging
    from datetime import UTC, datetime

    from .remediation.risk import compute_risk_for_alert

    logger = logging.getLogger(__name__)

    aois = load_aois()
    if aoi_id not in aois:
        raise ValueError(f"Zona desconocida: {aoi_id}. Disponibles: {', '.join(aois)}")
    aoi = aois[aoi_id]

    # --- Load active alerts ---
    active_path = S.PROCESSED / aoi_id / "gcov" / "active-comparison.json"
    if not active_path.exists():
        raise FileNotFoundError(
            f"No hay comparación activa en {active_path}. Ejecutar sarlab change primero."
        )
    period = json.loads(active_path.read_text(encoding="utf-8"))["period"]
    alerts_path = S.PROCESSED / aoi_id / "gcov" / period / "alerts_hvhv.geojson"
    if not alerts_path.exists():
        raise FileNotFoundError(f"No se encontró {alerts_path}")

    geojson = json.loads(alerts_path.read_text(encoding="utf-8"))
    features = geojson.get("features", [])
    logger.info("Remediación: %d manchas HV en %s", len(features), period)

    # --- Load exposure (crop_ha per alert id) ---
    exposure_path = S.DATA_DIR / "04_published" / "exposure" / f"{aoi_id}.json"
    exposure_by_id: dict = {}
    if exposure_path.exists():
        exp = json.loads(exposure_path.read_text(encoding="utf-8"))
        exposure_by_id = exp.get("alerts", {})

    # --- Load slope from agriculture.py output ---
    agr_path = S.DATA_DIR / "04_published" / "agriculture" / f"{aoi_id}.json"
    slope_by_id: dict[str, float] = {}
    if agr_path.exists():
        agr = json.loads(agr_path.read_text(encoding="utf-8"))
        # agriculture output has alerts list or dict keyed by alert id
        agr_alerts = agr.get("alerts", {})
        if isinstance(agr_alerts, dict):
            for aid, v in agr_alerts.items():
                slope_by_id[aid] = v.get("slope_mean_deg") or v.get("slope_deg")
        elif isinstance(agr_alerts, list):
            for v in agr_alerts:
                if "id" in v:
                    slope_by_id[v["id"]] = v.get("slope_mean_deg") or v.get("slope_deg")

    # --- Load live fires from catalog cache ---
    fires_cache = S.DATA_DIR / "catalog" / "live" / "fires.json"
    all_fires: list[dict] = []
    if fires_cache.exists():
        try:
            fc = json.loads(fires_cache.read_text(encoding="utf-8"))
            if isinstance(fc, dict) and fc.get("type") == "FeatureCollection":
                # GeoJSON FeatureCollection: extract feature dicts
                all_fires = fc.get("features", [])
            elif isinstance(fc, dict) and "detections" in fc:
                all_fires = fc["detections"]
            elif isinstance(fc, list):
                all_fires = fc
        except Exception:
            pass

    # --- Load earthquakes from live cache ---
    quakes_cache = S.DATA_DIR / "catalog" / "live" / "quakes.json"
    all_quakes: list[dict] = []
    if quakes_cache.exists():
        try:
            qc = json.loads(quakes_cache.read_text(encoding="utf-8"))
            all_quakes = qc.get("features", [])
        except Exception:
            pass

    # --- Load rainfall summary ---
    rain_path = S.DATA_DIR / "04_published" / "rainfall" / f"{aoi_id}.json"
    rain_7d: float | None = None
    if rain_path.exists():
        try:
            rj = json.loads(rain_path.read_text(encoding="utf-8"))
            rain_7d = rj.get("accumulated_mm") or rj.get("total_mm")
        except Exception:
            pass

    # --- SoilGrids centroid cache (avoid one API call per polygon) ---
    soil_cache: dict[str, dict] = {}

    def _centroid(geometry: dict) -> tuple[float, float]:
        """Return approximate centroid (lon, lat) of a polygon geometry."""
        coords = geometry.get("coordinates", [[]])[0]
        if not coords:
            return 0.0, 0.0
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return sum(lons) / len(lons), sum(lats) / len(lats)

    def _fires_near(lon: float, lat: float, radius_km: float = 2.0) -> list[dict]:
        import math
        result = []
        for f in all_fires:
            if isinstance(f, dict) and f.get("type") == "Feature":
                # GeoJSON Feature
                coords = f.get("geometry", {}).get("coordinates", [])
                flon = coords[0] if len(coords) >= 2 else None
                flat = coords[1] if len(coords) >= 2 else None
            else:
                flat = f.get("latitude") or f.get("lat")
                flon = f.get("longitude") or f.get("lon")
            if flat is None or flon is None:
                continue
            dlat = math.radians(lat - flat)
            dlon = math.radians(lon - flon)
            a = (math.sin(dlat / 2) ** 2
                 + math.cos(math.radians(flat)) * math.cos(math.radians(lat)) * math.sin(dlon / 2) ** 2)
            dist_km = 6371 * 2 * math.asin(min(1, math.sqrt(a)))
            if dist_km <= radius_km:
                result.append(f)
        return result

    def _quakes_near(lon: float, lat: float, radius_km: float = 50.0) -> list[dict]:
        import math
        result = []
        for q in all_quakes:
            coords = q.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2:
                continue
            qlon, qlat = coords[0], coords[1]
            dlat = math.radians(lat - qlat)
            dlon = math.radians(lon - qlon)
            a = (math.sin(dlat / 2) ** 2
                 + math.cos(math.radians(qlat)) * math.cos(math.radians(lat)) * math.sin(dlon / 2) ** 2)
            dist_km = 6371 * 2 * math.asin(min(1, math.sqrt(a)))
            if dist_km <= radius_km:
                q_copy = dict(q)
                q_copy["_distance_km"] = round(dist_km, 1)
                result.append(q_copy)
        return result

    # --- Process each alert ---
    results = []
    summary = {"total_alerts": 0, "high": 0, "medium": 0, "low": 0}

    for feat in features:
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        alert_id = props.get("id", "")

        lon, lat = _centroid(geom)

        # Soil: round to ~1 km grid to reduce API calls
        grid_key = f"{round(lon, 2)},{round(lat, 2)}"
        if offline or not grid_key:
            soil_info = None
        elif grid_key not in soil_cache:
            if not offline:
                from .remediation.soilgrids import fetch_soil
                soil_info = fetch_soil(lon, lat)
            else:
                soil_info = None
            soil_cache[grid_key] = soil_info
        else:
            soil_info = soil_cache[grid_key]

        # Merge exposure into props
        exp_data = exposure_by_id.get(alert_id, {})
        merged_props = {**props, **{
            "cropland_ha": exp_data.get("cropland_ha", props.get("cropland_ha")),
        }}

        risk = compute_risk_for_alert(
            merged_props,
            soil_info=soil_info,
            slope_deg=slope_by_id.get(alert_id),
            fires_nearby=_fires_near(lon, lat),
            quakes_nearby=_quakes_near(lon, lat),
            rain_mm_7d=rain_7d,
            soil_moisture=None,  # SME2 not yet ingested; placeholder
        )

        # Attach geometry for GeoJSON output
        risk["geometry"] = geom
        results.append(risk)

        summary["total_alerts"] += 1
        if risk["level"] == "alto":
            summary["high"] += 1
        elif risk["level"] == "medio":
            summary["medium"] += 1
        else:
            summary["low"] += 1

    # --- Publish ---
    output_dir = S.DATA_DIR / "04_published" / "remediation"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{aoi_id}.json"

    output = {
        "aoi_id": aoi_id,
        "period": period,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "nisar_revisit_days": 12,
        "soil_moisture_available": False,
        "note": (
            "NISAR SME2 (humedad del suelo) no disponible aún; factor excluido del índice. "
            "El índice se apoya en caída HV, pendiente, focos y lluvia."
        ),
        "disclaimer": (
            "Aviso de monitoreo. No reemplaza a INDECI ni a la autoridad local. "
            "Verificar en campo. NISAR revisita cada ~12 días; no es tiempo real."
        ),
        "summary": summary,
        "alerts": results,
    }

    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Publicado: %s", output_path)
    return {"output_path": str(output_path), "summary": summary}
