"""SoilGrids REST API client — fetches WRB class and texture per point.

API docs: https://rest.isric.org/soilgrids/v2.0/docs
License of data: CC BY 4.0 (ISRIC, 2021).
No API key required for non-commercial use.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
# Properties we care about for the risk index
PROPERTIES = ["wrb", "clay", "sand", "soc"]  # WRB class, clay %, sand %, soil organic carbon
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
            data = resp.json()
            return _parse_response(data)
        except Exception as exc:
            logger.warning("SoilGrids attempt %d failed: %s", attempt + 1, exc)
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))

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


def _parse_response(data: dict) -> dict[str, Any]:
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

    # WRB class — returned as a list of probable classes with probabilities
    wrb_layer = layers.get("wrb")
    wrb_code = "DEFAULT"
    wrb_name = "No clasificado"
    if wrb_layer:
        most_probable = wrb_layer.get("most_probable_wrbclass", "")
        if most_probable:
            # e.g. "Cambisols" → extract first two letters for our code
            wrb_name = most_probable
            wrb_code = most_probable[:2].upper() if len(most_probable) >= 2 else "DEFAULT"

    return {
        "wrb_code": wrb_code,
        "wrb_name": wrb_name,
        "clay_pct": _mean("clay"),
        "sand_pct": _mean("sand"),
        "soc_pct": _mean("soc"),
        "source": "SoilGrids (ISRIC)",
        "source_url": "https://www.isric.org/explore/soilgrids",
        "source_date": "2021-01-01",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
    }
