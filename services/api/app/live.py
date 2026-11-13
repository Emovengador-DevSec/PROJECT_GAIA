"""Fuentes complementarias oficiales, con caché atómica y sin claves en las respuestas."""

from __future__ import annotations

import csv
import io
import json
import math
import os
import tempfile
import threading
import time
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import httpx
from shapely import union_all
from shapely.geometry import Point, shape
from shapely.prepared import prep

CACHE = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[3] / "data")) / "catalog" / "live"
LOCKS = {name: threading.Lock() for name in ("quakes", "fires")}
FAILURES: dict[str, tuple[float, str]] = {}
TTL_SECONDS = 600
MAX_BYTES = 20_000_000
USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query"
FIRMS = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


@lru_cache(maxsize=1)
def _peru_boundary():
    path = Path(__file__).resolve().parents[3] / "apps/web/public/globe/peru-boundaries.geojson"
    features = json.loads(path.read_text(encoding="utf-8"))["features"]
    return prep(union_all([shape(item["geometry"]) for item in features if item["properties"]["level"] == 1]))


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _download(url: str, params: dict | None = None) -> bytes:
    # URLs are constructed by the server. Never accept an upstream URL from a client.
    with httpx.Client(timeout=httpx.Timeout(25, connect=8), follow_redirects=False) as client:
        with client.stream("GET", url, params=params, headers={"User-Agent": "GAIA-Alerta/1.0"}) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise ValueError("Respuesta del proveedor demasiado grande")
    return bytes(body)


def _number(value, low: float, high: float) -> float:
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError("Valor fuera del intervalo del proveedor")
    return result


def _quakes() -> list[dict]:
    start = (datetime.now(UTC) - timedelta(days=30)).date().isoformat()
    payload = json.loads(
        _download(
            USGS,
            {
                "format": "geojson",
                "starttime": start,
                "minmagnitude": 4,
                "minlatitude": -57,
                "maxlatitude": 14,
                "minlongitude": -85,
                "maxlongitude": -32,
                "limit": 2000,
                "orderby": "time",
                "eventtype": "earthquake",
            },
        )
    )
    result = []
    for feature in payload.get("features", [])[:2000]:
        try:
            p = feature["properties"]
            lon, lat, depth = feature["geometry"]["coordinates"][:3]
            lon, lat = _number(lon, -85, -32), _number(lat, -57, 14)
            magnitude = _number(p["mag"], 4, 10)
            occurred = datetime.fromtimestamp(_number(p["time"], 0, 1e14) / 1000, UTC).isoformat()
            event_id = str(feature["id"])[:100]
            result.append(
                {
                    "type": "Feature",
                    "id": "usgs-" + event_id,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "id": "usgs-" + event_id,
                        "kind": "quake",
                        "source": "USGS",
                        "source_kind": "complementary",
                        "title": f"Sismo de magnitud {magnitude:g}",
                        "place": str(p.get("place") or "Sudamérica")[:250],
                        "date": occurred,
                        "level": "alto" if magnitude >= 6 else "medio" if magnitude >= 5 else "bajo",
                        "confidence": "revisado" if p.get("status") == "reviewed" else "automático",
                        "metrics": {"magnitude": magnitude, "depth_km": _number(depth, -10, 1000)},
                        "source_url": "https://earthquake.usgs.gov/earthquakes/eventpage/" + event_id,
                        "note": ("Evento observado. La magnitud no equivale al daño local "
                                 "ni predice nuevos sismos."),
                        "granules": [],
                        "exposure": None,
                    },
                }
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return result


PUBLIC_FIRMS = (
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/"
    "J1_VIIRS_C2_South_America_24h.csv"
)


def _fire_urls(key: str) -> list[str]:
    if not key:
        return [PUBLIC_FIRMS]
    area = f"{FIRMS}/{key}/VIIRS_NOAA20_NRT/-82,-19,-68,1"
    start = (datetime.now(UTC) - timedelta(days=6)).date().isoformat()
    return [f"{area}/5", f"{area}/2/{start}"]


def _fires(key: str) -> list[dict]:
    result = {}
    peru = _peru_boundary()
    for url in _fire_urls(key):
        rows = csv.DictReader(io.StringIO(_download(url).decode("utf-8-sig")))
        if not rows.fieldnames or "latitude" not in rows.fieldnames:
            raise ValueError("FIRMS no devolvió un catálogo válido")
        for row in rows:
            if len(result) >= 20_000:
                break
            try:
                lat, lon = _number(row["latitude"], -19, 1), _number(row["longitude"], -82, -68)
                if not peru.covers(Point(lon, lat)):
                    continue
                time = row["acq_time"].zfill(4)
                occurred = datetime.fromisoformat(
                    f"{row['acq_date']}T{time[:2]}:{time[2:]}:00+00:00"
                ).isoformat()
                frp = _number(row["frp"], 0, 100_000)
                fid = f"firms-{row['acq_date']}-{time}-{lat}-{lon}"
                result[fid] = {
                    "type": "Feature",
                    "id": fid,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "id": fid,
                        "kind": "fire",
                        "source": "NASA FIRMS",
                        "source_kind": "complementary",
                        "title": "Foco de calor VIIRS",
                        "place": "Perú",
                        "date": occurred,
                        "level": "medio",
                        "confidence": str(row.get("confidence", "sin informar")),
                        "metrics": {"frp_mw": frp},
                        "source_url": "https://firms.modaps.eosdis.nasa.gov/map/",
                        "note": ("Anomalía térmica satelital. Requiere verificación local. "
                                 "No es temperatura del aire ni extensión quemada."),
                        "granules": [],
                        "exposure": None,
                    },
                }
            except (KeyError, TypeError, ValueError):
                continue
    return list(result.values())


def _read(path: Path) -> dict | None:
    try:
        if path.stat().st_size > MAX_BYTES * 2:
            return None
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached.get("type") == "FeatureCollection" and isinstance(cached.get("features"), list):
            stamp = datetime.fromisoformat(cached["last_updated"])
            if stamp.utcoffset() is None or stamp > datetime.now(UTC) + timedelta(minutes=5):
                return None
            return cached
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def _save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as fh:
            temp = Path(fh.name)
            json.dump(payload, fh, ensure_ascii=False, allow_nan=False)
        temp.replace(path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def collection(provider: str) -> dict:
    if provider not in LOCKS:
        raise ValueError("Fuente no válida")
    with LOCKS[provider]:
        path = CACHE / f"{provider}.json"
        cached = _read(path)
        if os.environ.get("SARLAB_OFFLINE") == "1":
            if cached:
                return {**cached, "stale": True, "status": "cached",
                        "message": "Modo local. Se muestra la última copia guardada con su fecha."}
            return {"type": "FeatureCollection", "features": [],
                    "source": "USGS" if provider == "quakes" else "NASA FIRMS",
                    "source_kind": "complementary", "status": "unavailable", "last_updated": None,
                    "stale": False, "message": "No hay una copia local guardada de esta fuente.",
                    "latency": "Minutos" if provider == "quakes" else "Horas"}
        if (
            cached
            and (datetime.now(UTC) - datetime.fromisoformat(cached["last_updated"])).total_seconds()
            < TTL_SECONDS
        ):
            return {**cached, "stale": False}
        source = "USGS" if provider == "quakes" else "NASA FIRMS"
        key = os.environ.get("FIRMS_MAP_KEY", "").strip()
        message = None
        failure = FAILURES.get(provider)
        if failure and time.monotonic() < failure[0]:
            message = failure[1]
        else:
            try:
                features = _quakes() if provider == "quakes" else _fires(key)
                payload = {
                    "type": "FeatureCollection",
                    "features": features,
                    "source": source,
                    "source_kind": "complementary",
                    "status": "ok",
                    "last_updated": _now(),
                    "stale": False,
                    "message": (
                        "Archivo público VIIRS NOAA-20 de las últimas 24 h."
                        if provider == "fires" and not key else None
                    ),
                    "latency": "Minutos" if provider == "quakes" else "Horas",
                }
                _save(path, payload)
                FAILURES.pop(provider, None)
                return payload
            except (httpx.HTTPError, OSError, ValueError, KeyError, TypeError):
                # Exception URLs may contain the FIRMS key, so never expose their text.
                message = f"No se pudo actualizar {source}. Intenta nuevamente en unos minutos."
                FAILURES[provider] = (time.monotonic() + 60, message)
        if cached:
            return {**cached, "stale": True, "status": "cached", "message": message}
        return {
            "type": "FeatureCollection",
            "features": [],
            "source": source,
            "source_kind": "complementary",
            "status": "unavailable",
            "last_updated": None,
            "stale": False,
            "message": message,
            "latency": "Minutos" if provider == "quakes" else "Horas",
        }
