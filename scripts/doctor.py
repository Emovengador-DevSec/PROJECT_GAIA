#!/usr/bin/env python3
"""Revisa herramientas, entorno, configuración y carpetas de datos.

Uso:
    python3 scripts/doctor.py                 # revisión completa
    python3 scripts/doctor.py --config-only   # solo configuración (para CI)

Código de salida: 0 si no hay errores, 1 si hay errores, 2 si falta PyYAML.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("Falta PyYAML. Instálalo con: pip install pyyaml")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
DATA = ROOT / "data"

errors: list[str] = []
warnings: list[str] = []


def error(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def load_yaml(path: Path):
    try:
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001
        error(f"{path.relative_to(ROOT)}: no se puede leer ({exc})")
        return None


def require_keys(path: Path, data, keys: list[str]) -> bool:
    if not isinstance(data, dict):
        error(f"{path.relative_to(ROOT)}: debe ser un mapa de campos")
        return False
    missing = [k for k in keys if k not in data]
    if missing:
        error(f"{path.relative_to(ROOT)}: faltan campos obligatorios: {', '.join(missing)}")
        return False
    return True


def check_tools() -> None:
    for tool in ("git", "uv", "pnpm"):
        if shutil.which(tool) is None:
            warn(f"Herramienta no encontrada: {tool}")


def check_env() -> None:
    # Inspect process capabilities only. Never open the user's credentials file.
    for key in ("EARTHDATA_TOKEN", "FIRMS_MAP_KEY"):
        if not os.environ.get(key):
            warn(f"Entorno: {key} no está configurada. El diagnóstico no abre .env.")


def check_config() -> None:
    if not CONFIG.exists():
        error("No existe la carpeta config/")
        return

    for name in ("app.yaml", "sources.yaml", "thresholds.yaml", "colormaps.yaml", "features.yaml"):
        path = CONFIG / name
        if not path.exists():
            error(f"Falta config/{name}")
            continue
        data = load_yaml(path)
        if name == "thresholds.yaml" and require_keys(path, data, ["coherence_min"]):
            value = data["coherence_min"].get("value") if isinstance(data["coherence_min"], dict) else None
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                error("config/thresholds.yaml: coherence_min.value debe ser un número entre 0 y 1")
        if name == "features.yaml" and isinstance(data, dict):
            for group in ("tabs", "layers"):
                for k, v in (data.get(group) or {}).items():
                    if not isinstance(v, bool):
                        error(f"config/features.yaml: {group}.{k} debe ser verdadero o falso")

    products = {}
    for path in sorted((CONFIG / "products").glob("*.yaml")):
        data = load_yaml(path)
        if require_keys(path, data, ["id", "source", "level", "format", "layers"]):
            if data["id"] != path.stem:
                error(f"{path.relative_to(ROOT)}: id '{data['id']}' no coincide con el nombre del archivo")
            products[data["id"]] = data

    sources_data = load_yaml(CONFIG / "sources.yaml") or {}
    source_ids = set((sources_data.get("sources") or {}).keys())
    for pid, pdata in products.items():
        if source_ids and pdata["source"] not in source_ids:
            error(f"config/products/{pid}.yaml: la fuente '{pdata['source']}' no existe en sources.yaml")

    phenomena = {}
    for path in sorted((CONFIG / "phenomena").glob("*.yaml")):
        data = load_yaml(path)
        if require_keys(path, data, ["id", "name", "signals", "products", "method"]):
            if data["id"] != path.stem:
                error(f"{path.relative_to(ROOT)}: id '{data['id']}' no coincide con el nombre del archivo")
            for prod in data["products"]:
                if prod not in products:
                    error(f"{path.relative_to(ROOT)}: el producto '{prod}' no existe en config/products/")
            phenomena[data["id"]] = data

    aoi_count = 0
    for path in sorted((CONFIG / "aois").glob("*.yaml")):
        data = load_yaml(path)
        if not require_keys(path, data, ["id", "name", "role", "status", "bbox", "phenomena"]):
            continue
        aoi_count += 1
        if data["id"] != path.stem:
            error(f"{path.relative_to(ROOT)}: id '{data['id']}' no coincide con el nombre del archivo")
        if data["role"] not in ("flagship", "support", "optional"):
            error(f"{path.relative_to(ROOT)}: role debe ser flagship, support u optional")
        if data["status"] not in ("approximate", "confirmed"):
            error(f"{path.relative_to(ROOT)}: status debe ser approximate o confirmed")
        bbox = data["bbox"]
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(v, (int, float)) for v in bbox)):
            error(f"{path.relative_to(ROOT)}: bbox debe ser [oeste, sur, este, norte]")
        else:
            west, south, east, north = bbox
            if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
                error(f"{path.relative_to(ROOT)}: bbox fuera de rango u ordenado al revés")
        for ph in data["phenomena"]:
            if ph not in phenomena:
                error(f"{path.relative_to(ROOT)}: el fenómeno '{ph}' no existe en config/phenomena/")
    aoi_ids = {p.stem for p in (CONFIG / "aois").glob("*.yaml")}
    for path in sorted((CONFIG / "stories").glob("*.yaml")):
        data = load_yaml(path)
        if require_keys(path, data, ["aoi", "title", "question", "hypotheses", "steps"]):
            if data["aoi"] not in aoi_ids:
                error(f"{path.relative_to(ROOT)}: la zona '{data['aoi']}' no existe en config/aois/")
    if aoi_count == 0:
        error("No hay ninguna zona en config/aois/")
    if sum(1 for _ in (CONFIG / "aois").glob("*.yaml")):
        flagships = 0
        for path in (CONFIG / "aois").glob("*.yaml"):
            d = load_yaml(path)
            if isinstance(d, dict) and d.get("role") == "flagship":
                flagships += 1
        if flagships > 1:
            warn("Hay más de una zona con role flagship; se recomienda una sola")


def check_data_dirs() -> None:
    expected = [
        "00_inbox", "01_raw", "02_interim", "03_processed",
        "04_published", "99_quarantine", "catalog",
    ]
    for name in expected:
        if not (DATA / name).is_dir():
            error(f"Falta la carpeta data/{name}/")

    manifest = DATA / "catalog" / "raw_checksums.json"
    if not manifest.exists():
        print("  (info) data/catalog/raw_checksums.json aún no existe: nada que verificar en 01_raw.")
        return
    try:
        entries = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        error(f"data/catalog/raw_checksums.json: no se puede leer ({exc})")
        return
    for rel, expected_sha in entries.items():
        path = DATA / "01_raw" / rel
        if not path.exists():
            error(f"01_raw: falta el archivo registrado {rel}")
            continue
        sha = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                sha.update(chunk)
        if sha.hexdigest() != expected_sha:
            error(f"01_raw: {rel} fue modificado (la suma de comprobación no coincide)")


def main() -> int:
    config_only = "--config-only" in sys.argv
    print("Revisando configuración...")
    check_config()
    if not config_only:
        print("Revisando herramientas...")
        check_tools()
        print("Revisando entorno...")
        check_env()
        print("Revisando carpetas de datos...")
        check_data_dirs()

    for w in warnings:
        print(f"  AVISO  {w}")
    for e in errors:
        print(f"  ERROR  {e}")
    print()
    if errors:
        print(f"Resultado: {len(errors)} error(es), {len(warnings)} aviso(s).")
        return 1
    print(f"Resultado: sin errores, {len(warnings)} aviso(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
