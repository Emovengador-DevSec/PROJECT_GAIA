"""Public NISAR orbital elements with bounded caching and explicit freshness."""

from __future__ import annotations

import json
import math
import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .live import CACHE as LIVE_CACHE
from .live import _download, _save

URL = "https://celestrak.org/NORAD/elements/gp.php?NAME=NISAR&FORMAT=json"
CACHE = LIVE_CACHE / "nisar-orbit.json"
LOCK = threading.Lock()
NUMBERS = (
    "MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER",
    "MEAN_ANOMALY", "EPHEMERIS_TYPE", "NORAD_CAT_ID", "ELEMENT_SET_NO", "REV_AT_EPOCH",
    "BSTAR", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT",
)


def _validate(raw: dict) -> dict:
    if raw.get("OBJECT_NAME") != "NISAR":
        raise ValueError("Satellite name does not match NISAR")
    epoch = datetime.fromisoformat(str(raw["EPOCH"]).removesuffix("Z")).replace(tzinfo=UTC)
    if abs((datetime.now(UTC) - epoch).total_seconds()) > 7 * 86400:
        raise ValueError("Orbital epoch exceeds the seven-day propagation window")
    result = {name: raw[name] for name in NUMBERS}
    if any(not isinstance(value, int | float) or not math.isfinite(value) for value in result.values()):
        raise ValueError("Invalid orbital elements")
    if not 4 < result["MEAN_MOTION"] < 18 or not 0 <= result["ECCENTRICITY"] < 1:
        raise ValueError("Invalid orbit")
    return {**result, "OBJECT_NAME": "NISAR", "OBJECT_ID": str(raw["OBJECT_ID"])[:32],
            "EPOCH": str(raw["EPOCH"]), "CLASSIFICATION_TYPE": "U"}


def _read(path: Path) -> dict | None:
    try:
        if path.stat().st_size > 50_000:
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        record["elements"] = _validate(record["elements"])
        updated = datetime.fromisoformat(record["fetched_at"])
        if updated.utcoffset() is None or updated > datetime.now(UTC) + timedelta(minutes=5):
            return None
        return record
    except (OSError, KeyError, TypeError, ValueError):
        return None


def elements() -> dict:
    with LOCK:
        cached = _read(CACHE)
        offline = os.environ.get("SARLAB_OFFLINE") == "1"
        fresh = cached and (
            datetime.now(UTC) - datetime.fromisoformat(cached["fetched_at"]) < timedelta(hours=6)
        )
        if not offline and not fresh:
            try:
                records = json.loads(_download(URL))
                row = next(item for item in records if item.get("OBJECT_NAME") == "NISAR")
                cached = {"elements": _validate(row),
                          "fetched_at": datetime.now(UTC).isoformat(timespec="seconds")}
                _save(CACHE, cached)
                fresh = True
            except (OSError, StopIteration, KeyError, TypeError, ValueError):
                pass
            except Exception:
                # Upstream failures must not return internal URLs or environment details.
                pass
        if not cached:
            return {"status": "unavailable", "source_url": URL,
                    "message": "No hay elementos orbitales recientes. Reintenta con conexión a CelesTrak."}
        return {**cached, "status": "ok" if fresh and not offline else "cached", "source_url": URL,
                "message": "Órbita propagada con elementos públicos. La franja de observación es aproximada."}
