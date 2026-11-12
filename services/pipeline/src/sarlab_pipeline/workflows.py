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
    available = set(list_layers(before, freq)) & set(list_layers(after, freq))
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
    aoi = load_aois()[aoi_id]
    thr = load_thresholds()
    epsg = gcov.product_epsg(before, freq)
    bbox = gcov.bbox_to_product_crs(aoi.bbox, epsg)
    wa = gcov.read_window(before, layer, bbox, freq)
    wb = gcov.read_window(after, layer, bbox, freq)
    a, b, ref = _align(wa, wb)
    a_db, b_db = boxcar(to_db(a), speckle), boxcar(to_db(b), speckle)
    d = diff_db(a_db, b_db)
    res = robust_threshold(d, thr.change_k_sigma)

    tag = f"{_date(wa.source)}__{_date(wb.source)}"
    out = S.PROCESSED / aoi_id / "gcov" / tag
    lid = f"lyr_{aoi_id}_gcov_diff-{layer.lower()}_{tag}"
    cog = write_cog(out / f"diff_{layer.lower()}_db.tif", d, ref.transform, epsg)
    write_cog(out / f"before_{layer.lower()}_db.tif", a_db, ref.transform, epsg)
    write_cog(out / f"after_{layer.lower()}_db.tif", b_db, ref.transform, epsg)
    man = M.build(lid, "backscatter_diff_db", f"Cambio de retrodispersión {layer[:2]}", "dB", "RdBu",
                  d, cog, aoi_id, {"a": _date(wa.source), "b": _date(wb.source)},
                  [wa.source, wb.source],
                  extra={"product": "GCOV", "layer": layer, "frequency": freq, "epsg": epsg,
                         "threshold_db": res.threshold_db, "method": "robust_mad_k_sigma"})
    M.write(man, out / f"manifest_{layer.lower()}.json")

    alerts = polygons(res.loss, ref.transform, thr.min_alert_pixels)
    px_area_ha = abs(ref.transform.a * ref.transform.e) / 1e4
    for i, f in enumerate(alerts):
        f["properties"] = {"id": f"alr_{aoi_id}_{tag}_{layer.lower()}_{i:03d}",
                           "phenomenon": "backscatter_loss",
                           "epsg": epsg, "layer_id": lid, "method": "robust_mad_k_sigma",
                           "date_range": [man["dates"]["a"], man["dates"]["b"]]}
    (out / f"alerts_{layer.lower()}.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "crs_epsg": epsg, "features": alerts}), encoding="utf-8")
    return {"manifest": man, "alerts": len(alerts),
            "loss_area_ha": round(float(res.loss.sum()) * px_area_ha, 2), "out_dir": str(out)}


def _date(name: str) -> str:
    import re
    m = re.search(r"_(\d{8})T\d{6}_", name)
    return f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}" if m else "unknown"
