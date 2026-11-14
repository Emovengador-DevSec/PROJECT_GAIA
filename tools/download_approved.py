"""Resume the two approved Ayacucho GCOV downloads without exposing signed URLs."""

import json
import logging
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import asf_search as asf
import requests
from dotenv import load_dotenv

from sarlab_pipeline.ingest import load_catalog
from sarlab_pipeline.settings import CATALOG, INBOX, INTERIM, RAW, ROOT, earthdata_token
from sarlab_pipeline.sources.nisar import HDF5_SIGNATURE

BLOCK = 8 * 1024 * 1024
APPROVED = {"2026-06-19": 1_954_545_664, "2026-10-05": 1_908_408_320}
CATALOG_NAME = "nisar_ayacucho-huanta_gcov.json"


def fetch_block(url, size, start, end, target, session):
    expected = end - start + 1
    if target.is_file() and target.stat().st_size == expected:
        return expected
    pending = target.with_suffix(".partial")
    for _ in range(3):
        try:
            with session.get(url, headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"},
                             stream=True, timeout=(12, 30)) as response:
                if response.status_code in {401, 403}:
                    raise RuntimeError(f"Acceso denegado al bloque (HTTP {response.status_code}).")
                content_range = f"bytes {start}-{end}/{size}"
                if response.status_code != 206 or response.headers.get("Content-Range") != content_range:
                    raise RuntimeError(f"ASF no devolvió el bloque solicitado (HTTP {response.status_code}).")
                downloaded = 0
                with pending.open("wb") as handle:
                    for chunk in response.iter_content(256 * 1024):
                        downloaded += len(chunk)
                        if downloaded > expected:
                            raise RuntimeError("El bloque recibido excede el intervalo solicitado.")
                        handle.write(chunk)
                if downloaded != expected:
                    raise requests.exceptions.ChunkedEncodingError("Bloque incompleto")
                pending.replace(target)
                return expected
        except requests.exceptions.RequestException:
            continue
    raise RuntimeError(f"ASF no completó el bloque que comienza en {start}; puedes reanudar la descarga.")


def download(entry, token):
    date = entry["start"][:10]
    size = APPROVED[date]
    url = entry["url"]
    name = entry["name"] + ".h5"
    if url != f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_PROVISIONAL_V1/{entry['name']}/{name}":
        raise RuntimeError("La URL del archivo no coincide con el catálogo oficial de NISAR.")
    if round(entry["size_mb"] * 1e6) != size:
        raise RuntimeError("El tamaño del archivo difiere del aprobado.")
    ingested = load_catalog()["items"].get(name)
    if ingested:
        original = (RAW / ingested["path"]).resolve()
        if original.is_relative_to(RAW.resolve()) and original.is_file() and original.stat().st_size == size:
            print(f"{date}: archivo completo ya ingresado", flush=True)
            return
        raise RuntimeError(f"Revisa la copia registrada de {date} con scripts/doctor.py.")
    destination = INBOX / name
    if destination.exists() and destination.stat().st_size == size:
        with destination.open("rb") as handle:
            if handle.read(8) == HDF5_SIGNATURE:
                print(f"{date}: archivo completo disponible", flush=True)
                return
    temporary = INBOX / ".ayacucho-download" / name
    temporary.mkdir(parents=True, exist_ok=True)
    intervals = [(start, min(size - 1, start + BLOCK - 1), temporary / f"{start}.block")
                 for start in range(0, size, BLOCK)]
    prefix = INTERIM / (name + ".sdk-partial")
    if prefix.is_file():
        prefix_size = prefix.stat().st_size
        with prefix.open("rb") as source:
            if source.read(8) == HDF5_SIGNATURE:
                for start, end, target in intervals:
                    if end >= prefix_size:
                        break
                    if target.is_file() and target.stat().st_size == end - start + 1:
                        continue
                    source.seek(start)
                    pending = target.with_suffix(".partial")
                    pending.write_bytes(source.read(end - start + 1))
                    pending.replace(target)

    def worker(group):
        with asf.ASFSession() as session:
            session.headers["Authorization"] = "Bearer " + token
            for start, end, path in group:
                yield fetch_block(url, size, start, end, path, session)

    def run_group(group):
        nonlocal total, next_message
        for count in worker(group):
            with progress_lock:
                total += count
                if total >= next_message or total == size:
                    print(f"{date}: {total / 1e6:.0f} / {size / 1e6:.0f} MB verificados", flush=True)
                    next_message = total + 64 * 1024 * 1024

    total = 0
    next_message = 1
    progress_lock = Lock()
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_group, intervals[offset::8]) for offset in range(8)]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                for other in futures:
                    other.cancel()
                raise

    assembled = temporary / "assembled.partial"
    with assembled.open("wb") as output:
        for _, _, block in intervals:
            with block.open("rb") as source:
                shutil.copyfileobj(source, output)
    with assembled.open("rb") as output:
        if assembled.stat().st_size != size or output.read(8) != HDF5_SIGNATURE:
            raise RuntimeError("La reconstrucción del archivo no coincide con el HDF5 de ASF.")
    if destination.exists() and destination.stat().st_size != 0:
        raise RuntimeError("Ya existe un HDF5 distinto en la carpeta de entrada. Se conservó para revisión.")
    os.replace(assembled, destination)
    for _, _, block in intervals:
        block.unlink()
    temporary.rmdir()
    prefix.unlink(missing_ok=True)
    print(f"{date}: HDF5 completo ({size:,} bytes)", flush=True)


def main():
    load_dotenv(ROOT / ".env", override=False)
    token = earthdata_token()
    if not token:
        raise RuntimeError("Falta EARTHDATA_TOKEN en la configuración local.")
    catalog = CATALOG / CATALOG_NAME
    if not catalog.is_file():
        catalog = ROOT / "config" / "catalog" / CATALOG_NAME
    granules = json.loads(catalog.read_text(encoding="utf-8"))["granules"]
    for date in APPROVED:
        matches = [entry for entry in granules if entry["start"][:10] == date
                   and entry["track"] == 75 and entry["frame"] == 171 and entry["direction"] == "ASCENDING"]
        if len(matches) != 1:
            raise RuntimeError(f"El catálogo no identifica un único GCOV aprobado para {date}.")
        download(matches[0], token)


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    try:
        main()
    except RuntimeError as exc:
        print(str(exc), flush=True)
        sys.exit(1)
    except Exception as exc:
        print("No se pudo completar la descarga. Tipo de error: " + type(exc).__name__, flush=True)
        sys.exit(1)
