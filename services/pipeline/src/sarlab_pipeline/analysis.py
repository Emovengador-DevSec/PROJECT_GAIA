"""Análisis que pide el reto: comparación de polarizaciones y series de tiempo.

- Polarizaciones: HH (co-polar) responde a superficie, agua y estructuras; HV (cruzada) a la
  dispersión de volumen de la vegetación. Comparar ambas ayuda a formular hipótesis físicas.
- Serie de tiempo: estadística de la zona en cada fecha disponible (N gránulos).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from . import settings as S
from .config import load_aois
from .processing.backscatter import to_db
from .readers import gcov

DATE_RE = re.compile(r"_(\d{8})T\d{6}_")


def granule_date(name: str) -> str:
    m = DATE_RE.search(name)
    return f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}" if m else "unknown"


def zone_stats(path: Path, bbox_wgs84, layers=("HHHH", "HVHV"), freq="frequencyA") -> dict:
    """Mediana y percentiles en dB de cada polarización dentro de la zona, más la razón HV/HH."""
    epsg = gcov.product_epsg(path, freq)
    bbox = gcov.bbox_to_product_crs(bbox_wgs84, epsg)
    available = set(gcov.list_layers(path, freq))
    out: dict = {"date": granule_date(Path(path).name), "granule": Path(path).name, "freq": freq}
    dbs = {}
    for layer in layers:
        if layer not in available:
            out[layer] = None
            continue
        w = gcov.read_window(path, layer, bbox, freq)
        db = to_db(w.data)
        dbs[layer] = db
        v = db[np.isfinite(db)]
        out[layer] = None if v.size == 0 else {
            "median_db": round(float(np.median(v)), 3),
            "p10_db": round(float(np.percentile(v, 10)), 3),
            "p90_db": round(float(np.percentile(v, 90)), 3),
            "valid_pct": round(100 * v.size / db.size, 2)}
    if "HHHH" in dbs and "HVHV" in dbs and dbs["HHHH"].shape == dbs["HVHV"].shape:
        ratio = dbs["HVHV"] - dbs["HHHH"]          # HV/HH en dB
        v = ratio[np.isfinite(ratio)]
        out["HV_HH_ratio_db"] = round(float(np.median(v)), 3) if v.size else None
    return out


def timeseries(aoi_id: str, files: list[Path], freq: str = "frequencyA") -> dict:
    aoi = load_aois()[aoi_id]
    rows = sorted((zone_stats(f, aoi.bbox, freq=freq) for f in files), key=lambda r: r["date"])
    result = {"aoi_id": aoi_id, "product": "GCOV", "freq": freq, "samples": rows,
              "note": "Estadística de la zona completa por fecha. Mismo track y dirección para comparar."}
    out = S.PROCESSED / aoi_id / "gcov" / "timeseries.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def polarization_summary(change_by_layer: dict[str, dict]) -> dict:
    """Resume qué polarización muestra más cambio: insumo para la hipótesis física."""
    summary = {k: {"loss_area_ha": v["loss_area_ha"], "alerts": v["alerts"]}
               for k, v in change_by_layer.items()}
    if summary:
        summary["strongest"] = max(summary, key=lambda k: summary[k]["loss_area_ha"])
    return summary
