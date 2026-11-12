"""API de Bailando con los SARs (FastAPI).

Rutas MVP: salud, configuración pública, zonas, capas (manifiestos) y alertas.
Teselas: si `titiler.core` está instalado se monta en /api/cog (teselas dinámicas desde COG).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(os.environ.get("SARLAB_ROOT", Path(__file__).resolve().parents[3]))
CONFIG = ROOT / "config"
PROCESSED = Path(os.environ.get("DATA_DIR", ROOT / "data")) / "03_processed"

app = FastAPI(title="Bailando con los SARs API", version="0.3.0")
app.add_middleware(CORSMiddleware,
                   allow_origins=[os.environ.get("ALLOWED_ORIGIN", "http://localhost:5173")],
                   allow_methods=["GET"], allow_headers=["*"])

try:  # teselas dinámicas opcionales
    from titiler.core.factory import TilerFactory
    app.include_router(TilerFactory().router, prefix="/api/cog", tags=["tiles"])
    TILES = True
except Exception:  # noqa: BLE001
    TILES = False


def _yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _manifests() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PROCESSED.glob("*/*/*/manifest*.json"))]


@app.get("/api/health")
def health():
    return {"status": "ok", "tiles": TILES, "layers": len(_manifests())}


@app.get("/api/config")
def public_config():
    """Configuración segura para el navegador (sin secretos)."""
    app_cfg = _yaml(CONFIG / "app.yaml")
    public = {k: v for k, v in app_cfg.items() if k in ("name", "language", "languages")}
    return {"features": _yaml(CONFIG / "features.yaml"),
            "colormaps": _yaml(CONFIG / "colormaps.yaml"), "app": public}


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


@app.get("/api/alerts")
def alerts(aoi: str = Query(..., pattern=r"^[a-z0-9-]+$")):
    feats = []
    for p in sorted((PROCESSED / aoi).glob("*/*/alerts*.geojson")):
        feats += json.loads(p.read_text(encoding="utf-8")).get("features", [])
    return {"type": "FeatureCollection", "features": feats}


AOI_PATTERN = r"^[a-z0-9-]+$"


@app.get("/api/stories/{aoi}")
def story(aoi: str):
    """Relato del caso: pregunta, hipótesis físicas, contexto humano y pasos de cámara."""
    if not __import__("re").match(AOI_PATTERN, aoi):
        raise HTTPException(422, detail="Identificador de zona inválido.")
    p = CONFIG / "stories" / f"{aoi}.yaml"
    if not p.exists():
        raise HTTPException(404, detail="Esta zona aún no tiene relato. Crea config/stories/<zona>.yaml.")
    return _yaml(p)


@app.get("/api/timeseries")
def timeseries(aoi: str = Query(..., pattern=AOI_PATTERN)):
    p = PROCESSED / aoi / "gcov" / "timeseries.json"
    if not p.exists():
        raise HTTPException(404, detail="Sin serie de tiempo. Ejecuta `sarlab timeseries`.")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/api/polarizations")
def polarizations(aoi: str = Query(..., pattern=AOI_PATTERN)):
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((PROCESSED / aoi).glob("*/*/polarizations.json"))]
