"""Exporta la API local y sus teselas NISAR como una copia estática verificable."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import math
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qsl, urlencode, urlsplit
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "apps" / "web" / "public"
PNG = b"\x89PNG\r\n\x1a\n"
SECRET_FIELD = re.compile(
    r"token|key|secret|password|authorization|credential|signature|(?:^|_)sig(?:$|_)", re.I)
SECRET_VALUE = re.compile(r"AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\."
                          r"[A-Za-z0-9_-]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+\S+")
LOCAL_PATH = re.compile(r"(?:^[A-Za-z]:[\\/]|^\\\\|^/(?:Users|home|tmp|var)/)")
PRIVATE_FIELDS = {"cog_path", "before_cog_path", "after_cog_path"}


def canonical(route: str) -> str:
    url = urlsplit(route)
    query = urlencode(sorted(parse_qsl(url.query, keep_blank_values=True)))
    return url.path + ("?" + query if query else "")


def public_data(value):
    """Conserva los datos de la API y omite rutas locales de los COG del servidor."""
    if isinstance(value, dict):
        return {key: public_data(item) for key, item in value.items() if key not in PRIVATE_FIELDS}
    if isinstance(value, list):
        return [public_data(item) for item in value]
    return value


def verify_public(value, location: str = "JSON") -> None:
    """Falla con el nombre del campo, sin imprimir el contenido detectado."""
    if isinstance(value, dict):
        for key, item in value.items():
            public_status = (key == "credentials" and isinstance(item, dict)
                             and all(value is False for value in item.values()))
            if SECRET_FIELD.search(key) and item not in (None, "", False) and not public_status:
                raise ValueError(f"Campo sensible en {location}.{key}. Se detuvo la publicación.")
            verify_public(item, f"{location}.{key}")
    elif isinstance(value, list):
        for item in value:
            verify_public(item, location + "[]")
    elif isinstance(value, str):
        if SECRET_VALUE.search(value) or LOCAL_PATH.search(value):
            raise ValueError(f"Contenido privado en {location}. Se detuvo la publicación.")
        if value.startswith(("http://", "https://")):
            url = urlsplit(value)
            if url.username or url.password or any(
                SECRET_FIELD.search(key) and item for key, item in parse_qsl(url.query)
            ):
                raise ValueError(f"URL con credenciales en {location}. Se detuvo la publicación.")


def tile_coordinates(bounds, maximum: int):
    west, south, east, north = bounds
    if not (-180 <= west < east <= 180 and -85.05112878 <= south < north <= 85.05112878):
        raise ValueError("La caja debe ser válida en Web Mercator y conservar oeste < este.")
    for zoom in range(maximum + 1):
        count = 2**zoom
        x_start = max(0, min(count - 1, math.floor((west + 180) / 360 * count)))
        x_end = max(0, min(count - 1, math.floor((east + 180) / 360 * count)))
        y_start = math.floor((1 - math.asinh(math.tan(math.radians(north))) / math.pi) / 2 * count)
        y_end = math.floor((1 - math.asinh(math.tan(math.radians(south))) / math.pi) / 2 * count)
        for x in range(x_start, x_end + 1):
            for y in range(max(0, y_start), min(count - 1, y_end) + 1):
                yield zoom, x, y


def safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Identificador de la API inválido para un archivo público.")
    return value


def local_api(value: str) -> str:
    url = urlsplit(value)
    if url.scheme != "http" or url.username or url.password or url.query or url.fragment:
        raise ValueError("Usa la dirección HTTP de la API local, sin credenciales ni parámetros.")
    try:
        loopback = url.hostname == "localhost" or ipaddress.ip_address(url.hostname or "").is_loopback
    except ValueError:
        loopback = False
    if not loopback or url.path not in ("", "/"):
        raise ValueError("La foto se genera desde la API local de GAIA.")
    return value.rstrip("/")


def export_snapshot(client: httpx.Client, destination: Path, maximum: int = 13, workers: int = 4) -> dict:
    if not 0 <= maximum <= 13 or not 1 <= workers <= 8:
        raise ValueError("Usa zoom entre 0 y 13 y entre 1 y 8 trabajadores.")
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".snapshot-", dir=destination.parent) as temporary:
        staging = Path(temporary)
        responses = {}

        def request(route: str, optional: bool = False) -> httpx.Response | None:
            for attempt in range(3):
                try:
                    response = client.get("/api" + route)
                    if optional and response.status_code == 404:
                        return None
                    response.raise_for_status()
                    if len(response.content) > 32 * 1024 * 1024:
                        raise ValueError("La respuesta supera 32 MiB. Revisa la exportación.")
                    return response
                except httpx.HTTPError:
                    if attempt == 2:
                        raise RuntimeError(
                            "La API local no completó una respuesta para la copia estática.") from None
            return None

        def get_json(route: str, optional: bool = False):
            response = request(route, optional)
            return public_data(response.json()) if response is not None else None

        def save(route: str, filename: str, value) -> None:
            verify_public(value, filename)
            target = staging / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False,
                                         separators=(",", ":")), encoding="utf-8")
            responses[canonical(route)] = filename

        zones = get_json("/aois")
        layers = get_json("/layers?active_only=true")
        if not isinstance(zones, list) or not isinstance(layers, list):
            raise ValueError("La API no devolvió las zonas y capas de GAIA.")
        if not any(layer.get("aoi_id") == "ayacucho-huanta" and layer.get("comparison") for layer in layers):
            raise ValueError("Falta la comparación NISAR real de Ayacucho. Completa G1 primero.")
        health = get_json("/health")
        if not health.get("tiles"):
            raise ValueError("La API debe servir las teselas NISAR antes de exportarlas.")
        # Capabilities belong to the snapshot. Server credential state stays local.
        health.update(offline=True, credentials={"earthdata": False, "firms": False}, layers=len(layers))
        save("/health", "api/health.json", health)
        save("/config", "api/config.json", get_json("/config"))
        save("/aois", "api/aois.json", zones)
        save("/layers", "api/layers.json", layers)
        responses[canonical("/layers?active_only=true")] = "api/layers.json"
        save("/alerts?include_live=true&active_only=true", "api/alerts.json",
             get_json("/alerts?include_live=true&active_only=true"))
        save("/alerts", "api/alerts-nisar.json", get_json("/alerts?active_only=true"))
        save("/orbit", "api/orbit.json", get_json("/orbit"))
        zone_bounds = {}
        for zone in zones:
            zone_id = safe_id(zone["id"])
            zone_bounds[zone_id] = zone["bbox"]
            folder = f"api/zones/{zone_id}"
            zone_layers = [item for item in layers if item["aoi_id"] == zone_id]
            for suffix in ("", "&active_only=true"):
                save(f"/layers?aoi={zone_id}{suffix}", f"{folder}/layers.json", zone_layers)
                save(f"/polarizations?aoi={zone_id}{suffix}", f"{folder}/polarizations.json",
                     get_json(f"/polarizations?aoi={zone_id}&active_only=true"))
            save(f"/stories/{zone_id}", f"{folder}/story.json",
                 get_json(f"/stories/{zone_id}", optional=True))
            save(f"/timeseries?aoi={zone_id}&allow_empty=true", f"{folder}/timeseries.json",
                 get_json(f"/timeseries?aoi={zone_id}&allow_empty=true"))
            responses[canonical(f"/timeseries?aoi={zone_id}")] = f"{folder}/timeseries.json"
            save(f"/rainfall/{zone_id}", f"{folder}/rainfall.json", get_json(f"/rainfall/{zone_id}"))
            for polarization in ("HHHH", "HVHV"):
                save(f"/trend?aoi={zone_id}&pol={polarization}", f"{folder}/trend-{polarization}.json",
                     get_json(f"/trend?aoi={zone_id}&pol={polarization}"))
            for product in ("GCOV", "GUNW", "SME2"):
                save(f"/catalog?aoi={zone_id}&product={product}", f"{folder}/catalog-{product}.json",
                     get_json(f"/catalog?aoi={zone_id}&product={product}"))
            contexts = get_json(f"/context/{zone_id}")
            save(f"/context/{zone_id}", f"{folder}/context.json", contexts)
            for context in contexts:
                if not context.get("available"):
                    continue
                product_id = safe_id(context["id"])
                for day in {context["date"], context.get("before", context["date"])}:
                    datetime.strptime(day, "%Y-%m-%d")
                    response = request(f"/context/{zone_id}/{product_id}/{day}.png")
                    if not response.content.startswith(PNG):
                        raise ValueError("La imagen de contexto no contiene un PNG válido.")
                    target = staging / "context" / zone_id / product_id / f"{day}.png"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(response.content)

        jobs = []
        for layer in layers:
            layer_id = safe_id(layer["id"])
            save(f"/layers/{layer_id}", f"api/layers/{layer_id}.json", layer)
            save(f"/validation/{layer_id}", f"api/validation/{layer_id}.json",
                 get_json(f"/validation/{layer_id}"))
            stages = [("change", "default")]
            if layer.get("comparison"):
                matching = {item.get("provenance", {}).get("layer") for item in layers
                            if item.get("comparison") and item.get("kind") == "backscatter_diff_db"
                            and item.get("aoi_id") == layer["aoi_id"] and item.get("dates") == layer["dates"]
                            and item["provenance"].get("granules") == layer["provenance"].get("granules")
                            and item["provenance"].get("frequency") == layer["provenance"].get("frequency")}
                palettes = ("default", "rgb") if {"HHHH", "HVHV"} <= matching else ("default",)
                stages.extend((stage, palette) for stage in ("before", "after") for palette in palettes)
            for zoom, x, y in tile_coordinates(zone_bounds[layer["aoi_id"]], maximum):
                for stage, palette in stages:
                    route = f"/tiles/{layer_id}/{stage}/{zoom}/{x}/{y}.png"
                    if palette == "rgb":
                        route += "?palette=rgb"
                    filename = f"tiles/{layer_id}/{stage}/{palette}/{zoom}/{x}/{y}.png"
                    jobs.append((route, filename))
        if len(jobs) > 18_000:
            raise ValueError("La selección supera 18.000 teselas. Reduce el zoom de la copia.")

        def write_tile(job):
            route, filename = job
            response = request(route)
            if not response.content.startswith(PNG):
                raise ValueError("Una tesela NISAR no contiene un PNG válido.")
            target = staging / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(response.content)

        print(f"Exportando {len(jobs)} teselas NISAR hasta zoom {maximum}…", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(write_tile, job) for job in jobs]
            for count, future in enumerate(as_completed(futures), 1):
                future.result()
                if count % 250 == 0 or count == len(jobs):
                    print(f"Teselas verificadas: {count}/{len(jobs)}", flush=True)
        files = []
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                body = path.read_bytes()
                files.append({"path": path.relative_to(staging).as_posix(), "size_bytes": len(body),
                              "sha256": hashlib.sha256(body).hexdigest()})
        manifest = {
            "schema_version": 1, "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "responses": responses, "tiles": {"minimum_level": 0, "maximum_level": maximum, "tile_size": 256},
            "files": files, "total_bytes": sum(item["size_bytes"] for item in files),
            "note": "Copia estática de datos reales. Las observaciones conservan su fecha y fuente.",
        }
        verify_public(manifest, "manifest.json")
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        backup = destination.with_name(f".snapshot-backup-{uuid4().hex}")
        if destination.exists():
            destination.rename(backup)
        try:
            staging.rename(destination)
        except OSError:
            if backup.exists():
                backup.rename(destination)
            raise
        if backup.exists():
            if (backup.parent.resolve() != destination.parent
                    or not backup.name.startswith(".snapshot-backup-")):
                raise ValueError("Carpeta de respaldo fuera del destino verificado.")
            shutil.rmtree(backup)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000", type=local_api)
    parser.add_argument("--max-zoom", default=13, type=int)
    parser.add_argument("--workers", default=4, type=int)
    args = parser.parse_args()
    with httpx.Client(base_url=args.api, timeout=90, follow_redirects=False) as client:
        manifest = export_snapshot(client, PUBLIC / "snapshot", args.max_zoom, args.workers)
    print(json.dumps({"generated_at": manifest["generated_at"], "files": len(manifest["files"]) + 1,
                      "size_mb": round(manifest["total_bytes"] / 1e6, 2)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
