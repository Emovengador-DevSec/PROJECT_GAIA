"""SoilGrids REST API client — fetches WRB class and texture per point.

API docs: https://rest.isric.org/soilgrids/v2.0/docs
License of data: CC BY 4.0 (ISRIC, 2021).
No API key required for non-commercial use.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
CLASSIFICATION_URL = "https://rest.isric.org/soilgrids/v2.0/classification/query"
# WRB comes from the classification endpoint; the properties endpoint has no "wrb" layer.
PROPERTIES = ["clay", "sand", "soc"]  # clay %, sand %, soil organic carbon
# WRB reference group (SoilGrids name) -> group code in config/nbs/soils.yaml
WRB_GROUPS = {
    "Andosols": "AN",
    "Leptosols": "LP", "Regosols": "LP",
    "Kastanozems": "KS", "Phaeozems": "KS", "Chernozems": "KS",
    "Cambisols": "CM",
}
GRID_DEG = 0.05  # ~5.5 km cells: SoilGrids fair use is ~5 requests/min
_PAUSE_S = 12.0
DEPTHS = ["0-5cm"]                             # top layer is most relevant for vegetation
_TIMEOUT = 15  # seconds


def fetch_soil(lon: float, lat: float, *, retries: int = 2) -> dict[str, Any]:
    """Return WRB class + texture for a geographic point.

    Returns a dict with keys:
        wrb_code, wrb_name, clay_pct, sand_pct, soc_pct, source, source_date, license
    On error or timeout, returns a dict with wrb_code='DEFAULT' and a note.
    """
    params = {
        "lon": lon,
        "lat": lat,
        "property": PROPERTIES,
        "depth": DEPTHS,
        "value": ["mean"],
    }
    for attempt in range(retries + 1):
        try:
            resp = requests.get(SOILGRIDS_URL, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            cls = requests.get(
                CLASSIFICATION_URL,
                params={"lon": lon, "lat": lat, "number_classes": 3},
                timeout=_TIMEOUT,
            )
            cls.raise_for_status()
            return _parse_response(resp.json(), cls.json())
        except Exception as exc:
            logger.warning("SoilGrids attempt %d failed: %s", attempt + 1, exc)
            if attempt < retries:
                time.sleep(5.0 * (attempt + 1))

    logger.error("SoilGrids unavailable for lon=%s lat=%s; using DEFAULT", lon, lat)
    return {
        "wrb_code": "DEFAULT",
        "wrb_name": "No disponible",
        "clay_pct": None,
        "sand_pct": None,
        "soc_pct": None,
        "source": "SoilGrids (ISRIC)",
        "source_url": "https://www.isric.org/explore/soilgrids",
        "source_date": "2021-01-01",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "note": "SoilGrids no disponible; se usó grupo DEFAULT",
    }


def _parse_response(data: dict, classification: dict | None = None) -> dict[str, Any]:
    """Parse SoilGrids v2 JSON response into a flat dict."""
    layers = {prop["name"]: prop for prop in data.get("properties", {}).get("layers", [])}

    def _mean(name: str) -> float | None:
        layer = layers.get(name)
        if not layer:
            return None
        depths = layer.get("depths", [])
        if not depths:
            return None
        values = depths[0].get("values", {})
        raw = values.get("mean")
        if raw is None:
            return None
        # SoilGrids returns scaled integers; divide by d_factor
        d_factor = layer.get("unit_measure", {}).get("d_factor", 1)
        return raw / d_factor if d_factor else raw

    # WRB reference group from the classification endpoint
    wrb_name = (classification or {}).get("wrb_class_name") or "No clasificado"
    wrb_code = WRB_GROUPS.get(wrb_name, "DEFAULT")
    probability = None
    for name, pct in (classification or {}).get("wrb_class_probability", []):
        if name == wrb_name:
            probability = pct

    return {
        "wrb_code": wrb_code,
        "wrb_name": wrb_name,
        "wrb_probability_pct": probability,
        "clay_pct": _mean("clay"),
        "sand_pct": _mean("sand"),
        "soc_pct": _mean("soc"),
        "source": "SoilGrids (ISRIC)",
        "source_url": "https://www.isric.org/explore/soilgrids",
        "source_date": "2021-01-01",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
    }


def cell_key(lon: float, lat: float) -> str:
    """Grid cell used to share one SoilGrids query among nearby polygons."""
    return f"{round(lon / GRID_DEG) * GRID_DEG:.2f},{round(lat / GRID_DEG) * GRID_DEG:.2f}"


def build_soil_cache(points: list[tuple[float, float]], out_path: Path) -> dict[str, Any]:
    """Query SoilGrids once per grid cell and store the result (resumable)."""
    cache: dict[str, Any] = {}
    if out_path.exists():
        cache = json.loads(out_path.read_text(encoding="utf-8")).get("cells", {})
    todo = sorted({cell_key(lon, lat) for lon, lat in points} - {
        k for k, v in cache.items() if v.get("wrb_name") not in (None, "No disponible")
    })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for i, key in enumerate(todo):
        lon, lat = (float(v) for v in key.split(","))
        cache[key] = fetch_soil(lon, lat)
        logger.info("SoilGrids %d/%d %s -> %s", i + 1, len(todo), key, cache[key]["wrb_name"])
        out_path.write_text(json.dumps({
            "source": "SoilGrids 2.0 (ISRIC)",
            "license": "CC BY 4.0",
            "grid_deg": GRID_DEG,
            "updated_at": datetime.now(tz=UTC).isoformat(),
            "cells": cache,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        if i + 1 < len(todo):
            time.sleep(_PAUSE_S)
    return cache
