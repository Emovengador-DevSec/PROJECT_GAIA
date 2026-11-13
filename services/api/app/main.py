"""API de GAIA Alerta: observaciones, procedencia, relatos y teselas COG locales."""

from __future__ import annotations

import json
import os
import re
from base64 import b64decode
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(os.environ.get("SARLAB_ROOT", Path(__file__).resolve().parents[3]))
load_dotenv(ROOT / ".env", override=False)
from . import live  # noqa: E402

CONFIG = ROOT / "config"
PROCESSED = Path(os.environ.get("DATA_DIR", ROOT / "data")) / "03_processed"
TRANSPARENT_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNgAAIAAAUAAXpeqz8AAAAASUVORK5CYII="
)

app = FastAPI(title="Bailando con los SARs API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("ALLOWED_ORIGIN", "http://localhost:5173")],
    allow_methods=["GET"],
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
def layers(aoi: str | None = Query(None, pattern=r"^[a-z0-9-]+$")):
    ms = _manifests()
    return [m for m in ms if aoi is None or m.get("aoi_id") == aoi]


@app.get("/api/layers/{layer_id}")
def layer(layer_id: str):
    for m in _manifests():
        if m["id"] == layer_id:
            return m
    raise HTTPException(404, detail="Capa no encontrada. Procesa la zona con `sarlab change`.")


def _local_cog(path_value: str | None) -> Path:
    if not path_value:
        raise HTTPException(404, "No existe esa observación en el manifiesto.")
    path = Path(path_value).resolve()
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


@app.get("/api/tiles/{layer_id}/{stage}/{z}/{x}/{y}.png")
def tile(
    layer_id: str, stage: Literal["change", "before", "after"], z: int, x: int, y: int,
    palette: Literal["default", "rgb"] = "default",
):
    if not TILES:
        raise HTTPException(503, "Instala las dependencias del servidor para servir capas radar.")
    if not 0 <= z <= 18 or not 0 <= x < 2**z or not 0 <= y < 2**z:
        raise HTTPException(422, "Coordenadas de tesela inválidas.")
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


@app.get("/api/alerts")
def alerts(aoi: str | None = Query(None, pattern=r"^[a-z0-9-]+$"), include_live: bool = False):
    feats = []
    pattern = f"{aoi}/*/*/alerts*.geojson" if aoi else "*/*/*/alerts*.geojson"
    for p in sorted(PROCESSED.glob(pattern)):
        payload = json.loads(p.read_text(encoding="utf-8"))
        for feature in payload.get("features", []):
            props = feature.get("properties", {})
            geometry = feature.get("geometry")
            epsg = props.get("epsg", payload.get("crs_epsg", 4326))
            if geometry and epsg != 4326:
                from rasterio.warp import transform_geom

                geometry = transform_geom(f"EPSG:{epsg}", "EPSG:4326", geometry)
            zone = p.relative_to(PROCESSED).parts[0]
            props = {
                **props,
                "kind": props.get("kind", "surface_change"),
                "source": "NISAR",
                "source_kind": "primary",
                "aoi_id": zone,
                "title": "Cambio de retrodispersión NISAR",
                "place": props.get("place", zone),
                "date": (props.get("date_range") or [None])[-1],
                "level": props.get("level", "medio"),
                "confidence": "por verificar",
                "note": "Cambio de señal radar. La causa requiere contraste con observaciones de campo.",
                "source_url": "https://nisar.jpl.nasa.gov/",
                "provisional": True,
                "metrics": {"area_ha": props.get("area_ha")},
                "exposure": None,
            }
            exposure_path = PROCESSED.parent / "04_published" / "exposure" / f"{zone}.json"
            if exposure_path.is_file():
                exposure = json.loads(exposure_path.read_text(encoding="utf-8"))
                item = exposure.get("alerts", {}).get(props.get("id"))
                if item:
                    props["exposure"] = {
                        **item,
                        "people": item.get("population"),
                        "crop_ha": item.get("cropland_ha"),
                    }
            feats.append({**feature, "geometry": geometry, "properties": props})
    sources = []
    if include_live:
        for provider in ("quakes", "fires"):
            feed = live.collection(provider)
            sources.append({k: v for k, v in feed.items() if k != "features"})
            feats.extend(feed["features"])
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
    p = PROCESSED / aoi / "gcov" / "timeseries.json"
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
def polarizations(aoi: str = Query(..., pattern=AOI_PATTERN)):
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((PROCESSED / aoi).glob("*/*/polarizations.json"))
    ]


WEB_DIST = ROOT / "apps" / "web" / "dist"
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
