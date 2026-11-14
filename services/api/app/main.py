"""API de GAIA Alerta: observaciones, procedencia, relatos y teselas COG locales."""

from __future__ import annotations

import json
import os
import re
import secrets
from base64 import b64decode
from collections import OrderedDict
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import cache, lru_cache
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Literal

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import reports

ROOT = Path(os.environ.get("SARLAB_ROOT", Path(__file__).resolve().parents[3]))
load_dotenv(ROOT / ".env", override=False)
from . import live  # noqa: E402

CONFIG = ROOT / "config"
PROCESSED = Path(os.environ.get("DATA_DIR", ROOT / "data")) / "03_processed"
TRANSPARENT_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNgAAIAAAUAAXpeqz8AAAAASUVORK5CYII="
)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop = None
    if os.environ.get("SARLAB_OFFLINE") != "1" and os.environ.get("SARLAB_WARM_FEEDS") == "1":
        stop = live.start_refresh()
    try:
        yield
    finally:
        if stop:
            stop.set()


class TextCompression(GZipMiddleware):
    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        text_api = path.startswith("/api/") and not path.endswith(".png")
        if text_api or path.endswith((".js", ".css", ".json", ".geojson")):
            await super().__call__(scope, receive, send)
        else:
            await self.app(scope, receive, send)


app = FastAPI(title="Bailando con los SARs API", version="0.3.0", lifespan=lifespan)
app.add_middleware(TextCompression, minimum_size=1024, compresslevel=5)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("ALLOWED_ORIGIN", "http://localhost:5173")],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

try:
    from rio_tiler.io import COGReader

    TILES = True
except ImportError:
    TILES = False


def _yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _manifests() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PROCESSED.glob("*/*/*/manifest*.json"))]


def _active_gcov(zone: str) -> str | None:
    selection = PROCESSED / zone / "gcov" / "active-comparison.json"
    if not selection.is_file():
        return None
    tag = json.loads(selection.read_text(encoding="utf-8")).get("period", "")
    valid = isinstance(tag, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}__\d{4}-\d{2}-\d{2}", tag)
    return tag if valid else None


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "tiles": TILES,
        "layers": len(_manifests()),
        "credentials": {
            "earthdata": bool(os.environ.get("EARTHDATA_TOKEN")),
            "firms": bool(os.environ.get("FIRMS_MAP_KEY")),
        },
        "offline": os.environ.get("SARLAB_OFFLINE") == "1",
    }


@app.get("/api/config")
def public_config():
    """Configuración segura para el navegador (sin secretos)."""
    app_cfg = _yaml(CONFIG / "app.yaml")
    public = {k: v for k, v in app_cfg.items() if k in ("name", "language", "languages")}
    return {
        "features": _yaml(CONFIG / "features.yaml"),
        "colormaps": _yaml(CONFIG / "colormaps.yaml"),
        "app": public,
    }


@app.get("/api/aois")
def aois():
    return [_yaml(p) for p in sorted((CONFIG / "aois").glob("*.yaml"))]


@app.get("/api/layers")
def layers(aoi: str | None = Query(None, pattern=r"^[a-z0-9-]+$"), active_only: bool = False):
    active = cache(_active_gcov)
    ms = _manifests()
    return [m for m in ms if (aoi is None or m.get("aoi_id") == aoi)
            and (not active_only or m.get("provenance", {}).get("product") != "GCOV"
                 or not (tag := active(m["aoi_id"]))
                 or f"{m['dates']['a']}__{m['dates']['b']}" == tag)]


@app.get("/api/layers/{layer_id}")
def layer(layer_id: str):
    for m in _manifests():
        if m["id"] == layer_id:
            return m
    raise HTTPException(404, detail="Capa no encontrada. Procesa la zona con `sarlab change`.")


def _local_cog(path_value: str | None) -> Path:
    if not path_value:
        raise HTTPException(404, "No existe esa observación en el manifiesto.")
    path = (PROCESSED / path_value).resolve()
    if not path.is_relative_to(PROCESSED.resolve()) or not path.is_file():
        raise HTTPException(404, "El archivo procesado no está disponible localmente.")
    return path


def _rgb_tile(manifest: dict, stage: str, x: int, y: int, z: int) -> bytes:
    from rio_tiler.utils import render

    from sarlab_pipeline.processing.false_color import backscatter_rgb

    provenance = manifest["provenance"]
    matches = {
        source["provenance"]["layer"]: source
        for source in _manifests()
        if source.get("comparison") and source.get("kind") == "backscatter_diff_db"
        and source.get("aoi_id") == manifest["aoi_id"] and source.get("dates") == manifest["dates"]
        and source.get("provenance", {}).get("layer") in ("HHHH", "HVHV")
        and source["provenance"].get("frequency") == provenance.get("frequency")
        and source["provenance"].get("granules") == provenance["granules"]
    }
    if not {"HHHH", "HVHV"} <= matches.keys():
        raise HTTPException(404, "Se necesitan HH y HV de las mismas dos observaciones.")
    bands = []
    for polarization in ("HHHH", "HVHV"):
        path = _local_cog(matches[polarization]["comparison"].get(stage + "_cog_path"))
        with COGReader(str(path)) as cog:
            bands.append(cog.tile(x, y, z, tilesize=256).array[0].filled(float("nan")))
    rgb, mask = backscatter_rgb(*bands)
    return render(rgb, mask, img_format="PNG")


TILE_REQUESTS_PER_MINUTE = int(os.environ.get("SARLAB_TILE_REQUESTS_PER_MINUTE", "0"))
TILE_REQUESTS: OrderedDict[str, tuple[float, int]] = OrderedDict()
TILE_LOCK = Lock()


def _check_tile_rate(request: Request) -> None:
    if TILE_REQUESTS_PER_MINUTE <= 0 or request.client is None:
        return
    now = monotonic()
    host = request.client.host
    with TILE_LOCK:
        while TILE_REQUESTS and next(iter(TILE_REQUESTS.values()))[0] + 60 <= now:
            TILE_REQUESTS.popitem(last=False)
        if host not in TILE_REQUESTS and len(TILE_REQUESTS) >= 8192:
            raise HTTPException(
                429, "El servidor alcanzó el límite de solicitudes.", headers={"Retry-After": "60"},
            )
        start, count = TILE_REQUESTS.get(host, (now, 0))
        if count >= TILE_REQUESTS_PER_MINUTE:
            raise HTTPException(
                429, "Demasiadas solicitudes de teselas.",
                headers={"Retry-After": str(int(start + 61 - now))},
            )
        TILE_REQUESTS[host] = start, count + 1


@app.get("/api/tiles/{layer_id}/{stage}/{z}/{x}/{y}.png")
def tile(
    layer_id: str, stage: Literal["change", "before", "after"], z: int, x: int, y: int,
    palette: Literal["default", "rgb"] = "default", *, request: Request = None,
):
    if not TILES:
        raise HTTPException(503, "Instala las dependencias del servidor para servir capas radar.")
    if not 0 <= z <= 18 or not 0 <= x < 2**z or not 0 <= y < 2**z:
        raise HTTPException(422, "Coordenadas de tesela inválidas.")
    if request is not None:
        _check_tile_rate(request)
    manifest = layer(layer_id)
    from rio_tiler.errors import TileOutsideBounds

    if palette == "rgb":
        if stage == "change" or manifest.get("kind") != "backscatter_diff_db":
            raise HTTPException(422, "El falso color se aplica a las observaciones antes y después.")
        try:
            body = _rgb_tile(manifest, stage, x, y, z)
        except TileOutsideBounds:
            body = TRANSPARENT_PNG
        return Response(
            content=body, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"},
        )

    path_value = (
        manifest.get("cog_path")
        if stage == "change"
        else manifest.get("comparison", {}).get(stage + "_cog_path")
    )
    path = _local_cog(path_value)
    from rio_tiler.colormap import cmap

    limits = (
        manifest.get("range", {}) if stage == "change" else manifest.get("comparison", {}).get("range", {})
    )
    low, high = limits.get("min"), limits.get("max")
    low = float(low) if low is not None else -35.0
    high = float(high) if high is not None else 0.0
    if high <= low:
        high = low + 1
    name = str(manifest.get("colormap", "rdbu")).lower() if stage == "change" else "gray"
    try:
        with COGReader(str(path)) as cog:
            image = cog.tile(x, y, z, tilesize=256)
            image.rescale(in_range=((low, high),))
            body = image.render(img_format="PNG", colormap=cmap.get(name))
    except TileOutsideBounds:
        # A fully transparent pixel can be drawn at any tile size.
        body = TRANSPARENT_PNG
    return Response(content=body, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/catalog")
def catalog(
    aoi: str = Query(..., pattern=r"^[a-z0-9-]+$"), product: Literal["GCOV", "GUNW", "SME2"] = "GCOV",
):
    from sarlab_pipeline.sources.nisar import load_cached_catalog

    try:
        result = load_cached_catalog(aoi, product, PROCESSED.parent / "catalog")
        if result is None:
            result = load_cached_catalog(aoi, product, CONFIG / "catalog")
    except (OSError, ValueError) as exc:
        raise HTTPException(503, "El catálogo local requiere volver a consultarse en ASF.") from exc
    if result is None:
        return {
            "aoi_id": aoi,
            "product": product,
            "source": "ASF DAAC",
            "granules": [],
            "message": "Consulta el catálogo NISAR para esta zona con sarlab search.",
        }
    return result


def _observation_date(day: str | None, granules: list[str]) -> str | None:
    if day:
        for granule in granules:
            match = re.search(r"_(\d{8}T\d{6})_\d{8}T\d{6}_", granule)
            if match and match[1][:8] == day.replace("-", ""):
                try:
                    return datetime.strptime(match[1], "%Y%m%dT%H%M%S").replace(tzinfo=UTC).isoformat()
                except ValueError:
                    continue
    return day


@app.get("/api/alerts")
def alerts(aoi: str | None = Query(None, pattern=r"^[a-z0-9-]+$"), include_live: bool = False,
           active_only: bool = True):
    active = cache(_active_gcov)

    @cache
    def exposure_for(zone: str) -> dict:
        path = PROCESSED.parent / "04_published" / "exposure" / f"{zone}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    @cache
    def remediation_map_for(zone: str) -> dict:
        path = PROCESSED.parent / "04_published" / "remediation" / f"{zone}.json"
        if not path.is_file():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {alert["alert_id"]: alert for alert in data.get("alerts", []) if "alert_id" in alert}

    manifests = {manifest["id"]: manifest for manifest in _manifests()}
    feats = []
    pattern = f"{aoi}/*/*/alerts*.geojson" if aoi else "*/*/*/alerts*.geojson"
    for p in sorted(PROCESSED.glob(pattern)):
        zone, product, period, _ = p.relative_to(PROCESSED).parts
        if active_only and product == "gcov" and (tag := active(zone)) and tag != period:
            continue
        payload = json.loads(p.read_text(encoding="utf-8"))
        for feature in payload.get("features", []):
            props = feature.get("properties", {})
            geometry = feature.get("geometry")
            epsg = props.get("epsg", payload.get("crs_epsg", 4326))
            if geometry:
                from rasterio.warp import transform_geom

                geometry = transform_geom(f"EPSG:{epsg}", "EPSG:4326", geometry, precision=5)
            manifest = manifests.get(props.get("layer_id"), {})
            provenance = manifest.get("provenance", {})
            day = (props.get("date_range") or [None])[-1]
            granules = props.get("granules") or provenance.get("granules", [])
            polarization = provenance.get("layer")
            props = {
                **props,
                "kind": props.get("kind", "surface_change"),
                "source": "NISAR",
                "source_kind": "primary",
                "aoi_id": zone,
                "title": "Cambio de retrodispersión NISAR",
                "place": props.get("place", zone),
                "date": _observation_date(day, granules),
                "granules": granules,
                "polarization": polarization,
                "level": props.get("level", "medio"),
                "confidence": "por verificar",
                "note": "Cambio de señal radar. La causa requiere contraste con observaciones de campo.",
                "source_url": "https://nisar.jpl.nasa.gov/",
                "provisional": True,
                "metrics": {"area_ha": props.get("area_ha")},
                "comparison_summary": manifest.get("change_summary") if polarization == "HVHV" else None,
                "exposure": None,
                "remediation": None,
            }
            item = exposure_for(zone).get("alerts", {}).get(props.get("id"))
            if item:
                props["exposure"] = {
                    **item,
                    "people": item.get("population"),
                    "crop_ha": item.get("cropland_ha"),
                }
            rem_item = remediation_map_for(zone).get(props.get("id"))
            if rem_item:
                props["remediation"] = rem_item
                props["level"] = rem_item.get("level", props.get("level", "medio"))
            feats.append({**feature, "geometry": geometry, "properties": props})
    sources = []
    if include_live:
        for provider in ("quakes", "fires"):
            feed = live.collection(provider)
            sources.append({k: v for k, v in feed.items() if k != "features"})
            feats.extend({**feature, "properties": {**feature["properties"]}} for feature in feed["features"])

        climate_dir = PROCESSED.parent / "04_published" / "climate"
        if climate_dir.is_dir():
            for c_path in sorted(climate_dir.glob("*.json")):
                czone = c_path.stem
                if aoi and czone != aoi:
                    continue
                try:
                    cdata = json.loads(c_path.read_text(encoding="utf-8"))
                    coords = cdata.get("coordinates", [-74.15, -13.1])
                    for anom in cdata.get("anomalies", []):
                        feats.append({
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": coords},
                            "properties": {
                                **anom,
                                "aoi_id": czone,
                                "source_kind": "complementary",
                                "confidence": anom.get("confidence", "pronóstico meteorológico"),
                                "metrics": anom.get("metrics", {}),
                            },
                        })
                except Exception:
                    pass
    from .fire_cells import aggregate, region_name

    for feature in feats:
        if feature.get("properties", {}).get("kind") == "fire":
            lon, lat = feature["geometry"]["coordinates"][:2]
            feature["properties"]["place"] = region_name(lon, lat)
    priority = {"alto": 0, "medio": 1, "bajo": 2}
    feats.sort(key=lambda feature: str(feature.get("properties", {}).get("date") or ""), reverse=True)
    feats.sort(
        key=lambda f: (
            priority.get(f.get("properties", {}).get("level"), 3),
        ),
    )
    return {"type": "FeatureCollection", "features": feats, "sources": sources,
            "fire_cells": aggregate(feats)}


@app.get("/api/live/quakes")
def live_quakes():
    return live.collection("quakes")


@app.get("/api/live/fires")
def live_fires():
    return live.collection("fires")


@app.get("/api/community")
def community_index():
    from .community import publication

    data = publication(PROCESSED.parent / "04_published")
    if data is None:
        return None
    return {**data, "places": [{key: value for key, value in place.items() if key != "impact"}
                               for place in data["places"]]}


@app.get("/api/community/{place_id}")
def community_place(place_id: str):
    from .community import community_detail, publication

    published = PROCESSED.parent / "04_published"
    data = publication(published)
    entry = next((place for place in (data or {}).get("places", []) if place["id"] == place_id), None)
    if not entry:
        raise HTTPException(404, "No hay una ficha comunitaria para este lugar.")
    feeds = {provider: live.collection(provider) for provider in ("quakes", "fires")}
    weather = study_climate("ayacucho-huanta")
    thresholds = _yaml(CONFIG / "thresholds.yaml")["community"]
    return {**entry, **community_detail(entry, feeds, thresholds, weather)}


@app.get("/api/climate/{aoi}")
def study_climate(aoi: str):
    if not re.fullmatch(r"[a-z0-9-]+", aoi):
        raise HTTPException(422, "Identificador de zona inválido.")
    path = PROCESSED.parent / "04_published" / "climate" / f"{aoi}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


@app.get("/api/agriculture/{aoi}")
def study_agriculture(aoi: str):
    if not re.fullmatch(r"[a-z0-9-]+", aoi):
        raise HTTPException(422, "Identificador de zona inválido.")
    path = PROCESSED.parent / "04_published" / "agriculture" / f"{aoi}.json"
    if not path.is_file():
        return None
    return {key: value for key, value in json.loads(path.read_text(encoding="utf-8")).items()
            if key != "alerts"}


@app.get("/api/fire-history/{aoi}")
def study_fire_history(aoi: str):
    if not re.fullmatch(r"[a-z0-9-]+", aoi):
        raise HTTPException(422, "Identificador de zona inválido.")
    path = PROCESSED.parent / "04_published" / "fire-history" / f"{aoi}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _reports_db() -> Path:
    return PROCESSED.parent / "reports" / "reports.sqlite3"


@app.get("/api/reports")
def visible_reports():
    with _report_list_lock:
        payload = _published_reports(_reports_db(), int(monotonic() // 60))
    return Response(json.dumps(payload, ensure_ascii=False), media_type="application/json",
                    headers={"Cache-Control": "no-store"})


_report_list_lock = Lock()


@lru_cache(maxsize=1)
def _published_reports(path: Path, _minute: int) -> list[dict]:
    records = reports.list_reports(path, "visible")
    if not records:
        return records
    aoi = "ayacucho-huanta"
    period = _active_gcov(aoi)
    hv = PROCESSED / aoi / "gcov" / (period or "") / "alerts_hvhv.geojson"
    areas = _hv_areas(hv, hv.stat().st_mtime_ns) if period and hv.is_file() else []
    return reports.annotate(records, live.collection("fires")["features"], areas)


@lru_cache(maxsize=1)
def _hv_areas(path: Path, _modified: int):
    from shapely.geometry import shape

    return [shape(item["geometry"]) for item in json.loads(path.read_text(encoding="utf-8"))["features"]]


@app.post("/api/reports", status_code=201)
async def submit_report(request: Request):
    origin = request.headers.get("origin")
    allowed = {str(request.base_url).rstrip("/"), os.environ.get("ALLOWED_ORIGIN", "http://localhost:5173")}
    if origin and origin not in allowed and request.headers.get("sec-fetch-site") != "same-origin":
        raise HTTPException(403, "Abre la ficha desde GAIA para enviar un reporte.")
    if request.headers.get("content-type", "").partition(";")[0].strip() != "application/json":
        raise HTTPException(415, "Envía un reporte en JSON.")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 4096:
            raise HTTPException(413, "El reporte supera el tamaño permitido.")
        body.extend(chunk)
    try:
        report = reports.ReportIn.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(422, "Revisa el tipo, ubicación, fecha y nota. Evita datos de contacto.") from exc
    west, south, east, north = _yaml(CONFIG / "aois" / "ayacucho-huanta.yaml")["bbox"]
    if not (west <= report.lon <= east and south <= report.lat <= north):
        raise HTTPException(422, "Selecciona una ubicación dentro de la zona de estudio de Ayacucho.")
    if not reports.allow_submission(request.client.host if request.client else "unknown"):
        raise HTTPException(
            429, "Alcanzaste el límite de reportes por hora.", headers={"Retry-After": "3600"},
        )
    from starlette.concurrency import run_in_threadpool

    ident = await run_in_threadpool(reports.create, _reports_db(), report)
    return {"id": ident, "status": "pending"}


def _require_moderator(token: str | None) -> None:
    expected = os.environ.get("GAIA_REPORTS_ADMIN_TOKEN", "")
    prefix = "Bearer "
    if not expected or not token or not token.startswith(prefix) or not secrets.compare_digest(
        token[len(prefix):].encode(), expected.encode(),
    ):
        raise HTTPException(403, "Se requiere acceso de moderación.")


@app.get("/api/reports/moderation")
def pending_reports(authorization: str | None = Header(None)):
    _require_moderator(authorization)
    return Response(json.dumps(reports.list_reports(_reports_db(), "pending"), ensure_ascii=False),
                    media_type="application/json", headers={"Cache-Control": "no-store"})


@app.patch("/api/reports/moderation/{report_id}", status_code=204)
def moderate_report(
    report_id: str, action: Literal["visible", "rejected"], authorization: str | None = Header(None),
):
    _require_moderator(authorization)
    with _report_list_lock:
        valid_id = re.fullmatch(r"[a-f0-9]{32}", report_id)
        if not valid_id or not reports.moderate(_reports_db(), report_id, action):
            raise HTTPException(404, "Reporte no encontrado o transición no disponible.")
        _published_reports.cache_clear()
    return Response(status_code=204)


@app.get("/api/orbit")
def nisar_orbit():
    from .orbit import elements

    return elements()


AOI_PATTERN = r"^[a-z0-9-]+$"


def _context_image(aoi: str, product: str, day: str) -> Path:
    return PROCESSED.parent / "04_published" / "context" / aoi / f"{product}-{day}.png"


@app.get("/api/context/{aoi}")
def study_context(aoi: str):
    if not re.fullmatch(AOI_PATTERN, aoi):
        raise HTTPException(422, "Identificador de zona inválido.")
    return [
        {**item, "available": all(
            _context_image(aoi, item["id"], day).is_file()
            for day in (item["date"], item.get("before", item["date"]))
        )}
        for item in _yaml(CONFIG / "context.yaml").get(aoi, [])
    ]


@app.get("/api/context/{aoi}/{product}/{day}.png")
def context_image(aoi: str, product: str, day: str):
    for item in study_context(aoi):
        if item["id"] == product and day in (item["date"], item.get("before")) and item["available"]:
            return FileResponse(_context_image(aoi, product, day), media_type="image/png")
    raise HTTPException(404, "No hay una imagen complementaria para esa fecha.")


@app.get("/api/validation/{layer_id}")
def validation(layer_id: str):
    manifest = layer(layer_id)
    path = PROCESSED.parent / "04_published" / "validation" / f"{manifest['id']}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


@app.get("/api/rainfall/{aoi}")
def rainfall(aoi: str):
    if not re.fullmatch(AOI_PATTERN, aoi):
        raise HTTPException(422, "Identificador de zona inválido.")
    path = PROCESSED.parent / "04_published" / "rainfall" / f"{aoi}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


@app.get("/api/stories/{aoi}")
def story(aoi: str):
    """Relato del caso: pregunta, hipótesis físicas, contexto humano y pasos de cámara."""
    if not re.fullmatch(AOI_PATTERN, aoi):
        raise HTTPException(422, detail="Identificador de zona inválido.")
    p = CONFIG / "stories" / f"{aoi}.yaml"
    if not p.exists():
        raise HTTPException(404, detail="Esta zona aún no tiene relato. Crea config/stories/<zona>.yaml.")
    return _yaml(p)


@app.get("/api/timeseries")
def timeseries(aoi: str = Query(..., pattern=AOI_PATTERN), allow_empty: bool = False):
    tag = _active_gcov(aoi)
    directory = PROCESSED / aoi / "gcov"
    p = (directory / tag if tag else directory) / "timeseries.json"
    if not p.exists():
        if allow_empty:
            return {"aoi_id": aoi, "samples": []}
        raise HTTPException(404, detail="Sin serie de tiempo. Ejecuta `sarlab timeseries`.")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/api/trend")
def trend(aoi: str = Query(..., pattern=AOI_PATTERN), pol: Literal["HHHH", "HVHV"] = "HVHV"):
    from .trend import project

    return project(timeseries(aoi, allow_empty=True), pol)


@app.get("/api/polarizations")
def polarizations(aoi: str = Query(..., pattern=AOI_PATTERN), active_only: bool = False):
    tag = _active_gcov(aoi) if active_only else None
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((PROCESSED / aoi).glob("*/*/polarizations.json"))
        if not tag or p.parent.parent.name != "gcov" or p.parent.name == tag
    ]


@app.get("/api/remediation/{aoi}")
def remediation(aoi: str):
    if not re.fullmatch(AOI_PATTERN, aoi):
        raise HTTPException(422, "Identificador de zona inválido.")
    path = PROCESSED.parent / "04_published" / "remediation" / f"{aoi}.json"
    if not path.is_file():
        raise HTTPException(
            404, detail="No hay datos de remediación para esta zona. Ejecuta `sarlab remediation --aoi <zona>`."
        )
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/remediation/{aoi}/{zone_id}")
def remediation_zone(aoi: str, zone_id: str):
    if not re.fullmatch(AOI_PATTERN, aoi):
        raise HTTPException(422, "Identificador de zona inválido.")
    path = PROCESSED.parent / "04_published" / "remediation" / f"{aoi}.json"
    if not path.is_file():
        raise HTTPException(
            404, detail="No hay datos de remediación para esta zona. Ejecuta `sarlab remediation --aoi <zona>`."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    for alert in data.get("alerts", []):
        if alert.get("alert_id") == zone_id:
            return alert
    raise HTTPException(404, detail="Mancha no encontrada en los datos de remediación.")


WEB_DIST = ROOT / "apps" / "web" / "dist"
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
