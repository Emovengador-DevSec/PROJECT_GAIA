"""Búsqueda y descarga de productos NISAR en ASF DAAC.

Verificado en la documentación de ASF (nov. 2026):
- asf_search: dataset='NISAR', processingLevel='GCOV' | 'GUNW' | 'GOFF' | 'GSLC' | 'SME2'.
- Madurez: dataMaturity='PROVISIONAL' (calibrado) o 'BETA' (precalibración).
- earthaccess short_name: 'NISAR_L2_GCOV_PROVISIONAL_V1' (y equivalentes).
- Cada búsqueda devuelve también archivos QA_STATS: se filtran por extensión .h5.
Revisa https://nisar-docs.asf.alaska.edu/asf-search si cambia la API.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from ..settings import INBOX, earthdata_token

PRODUCTS = {"GCOV", "GUNW", "GOFF", "GSLC", "SME2"}
HDF5_SIGNATURE = b"\x89HDF\r\n\x1a\n"


def load_cached_catalog(aoi_id: str, product: str = "GCOV", catalog_dir: Path | None = None) -> dict | None:
    """Read public ASF metadata previously saved by `sarlab search --save-catalog`."""
    from ..settings import CATALOG

    if not re.fullmatch(r"[a-z0-9-]+", aoi_id) or product not in PRODUCTS:
        raise ValueError("Zona o producto de catálogo inválido.")
    path = (catalog_dir or CATALOG) / f"nisar_{aoi_id}_{product.lower()}.json"
    if not path.is_file():
        return None
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("El catálogo supera el tamaño máximo de 4 MB.")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(catalog, dict)
            or catalog.get("aoi_id") != aoi_id or catalog.get("product") != product
            or not isinstance(catalog.get("granules"), list)):
        raise ValueError("Los metadatos del catálogo no coinciden con la zona y el producto.")
    return catalog


@dataclass
class Granule:
    name: str
    url: str
    start: str
    direction: str | None
    track: int | None
    size_mb: float | None
    frame: int | None = None
    polarizations: tuple[str, ...] = ()


def _size_mb(props: dict, filename: str) -> float | None:
    """ASF NISAR supplies a per-file bytes mapping; older products use a number."""
    raw = props.get("bytes")
    if isinstance(raw, dict):
        entry = raw.get(filename, {})
        raw = entry.get("bytes") if isinstance(entry, dict) else entry
    try:
        size = float(raw)
    except (TypeError, ValueError):
        return None
    return size / 1e6 if size > 0 else None


def search(wkt: str, start: date, end: date, product: str = "GCOV",
           maturity: str = "PROVISIONAL", direction: str | None = None,
           max_results: int = 1000, track: int | None = None,
           frame: int | None = None) -> list[Granule]:
    """Busca gránulos NISAR que intersectan la zona. Requiere `asf_search` instalado."""
    import asf_search as asf  # import tardío: solo se necesita al buscar

    if product not in PRODUCTS:
        raise ValueError(f"Producto no soportado: {product}")
    if start > end:
        raise ValueError("La fecha inicial debe ser anterior o igual a la final.")
    if not 1 <= max_results <= 1000:
        raise ValueError("max_results debe estar entre 1 y 1000.")
    opts = dict(dataset="NISAR", processingLevel=product, intersectsWith=wkt,
                start=start.isoformat(), end=end.isoformat(),
                dataMaturity=maturity, maxResults=max_results)
    if direction:
        opts["flightDirection"] = direction.upper()
    results = asf.search(**opts)

    granules: list[Granule] = []
    for r in results:
        props = r.properties
        url = props.get("url") or ""
        filename = Path(url).name
        if not url.endswith(".h5") or filename.endswith("_QA_STATS.h5"):
            continue  # descarta QA_STATS y auxiliares
        if track is not None and props.get("pathNumber") != track:
            continue
        if frame is not None and props.get("frameNumber") != frame:
            continue
        granules.append(Granule(
            name=props.get("fileID") or props.get("sceneName") or Path(url).stem,
            url=url,
            start=props.get("startTime", ""),
            direction=props.get("flightDirection"),
            track=props.get("pathNumber"),
            size_mb=_size_mb(props, filename),
            frame=props.get("frameNumber"),
            polarizations=tuple(props.get("mainBandPolarization") or []),
        ))
    return sorted(granules, key=lambda g: g.start)


def download(granules: list[Granule], dest: Path = INBOX, processes: int = 2) -> list[Path]:
    """Descarga a data/00_inbox/. Luego `sarlab ingest` los valida y mueve a 01_raw."""
    import asf_search as asf
    from asf_search.exceptions import ASFAuthenticationError

    if not granules:
        return []
    for granule in granules:
        url = urlsplit(granule.url)
        if (url.scheme != "https" or url.hostname != "nisar.asf.earthdatacloud.nasa.gov"
                or url.username or url.password or url.port not in (None, 443)):
            raise ValueError("La descarga autenticada exige una URL oficial de NISAR en ASF.")

    token = earthdata_token()
    if not token:
        raise RuntimeError("Falta EARTHDATA_TOKEN en el entorno (.env). Créalo en urs.earthdata.nasa.gov.")
    session = asf.ASFSession()
    try:
        session.auth_with_token(token)
    except ASFAuthenticationError:
        # Some EDL tokens are accepted by the protected object while the SDK's
        # separate token-introspection endpoint rejects them. Verify the object itself.
        session.headers.update({"Authorization": "Bearer " + token})
        try:
            with session.get(granules[0].url, headers={"Range": "bytes=0-7"},
                             stream=True, timeout=30) as response:
                signature = (
                    next(response.iter_content(chunk_size=8), b"")
                    if response.status_code in (200, 206) else b""
                )
                accepted = signature == HDF5_SIGNATURE
        except Exception:
            raise RuntimeError("No se pudo verificar el acceso protegido a NISAR.") from None
        if not accepted:
            raise RuntimeError("Earthdata no autorizó el archivo NISAR solicitado.") from None
    dest.mkdir(parents=True, exist_ok=True)
    asf.download_urls([g.url for g in granules], str(dest), session=session, processes=processes)
    paths = [dest / Path(g.url).name for g in granules]
    for granule, path in zip(granules, paths, strict=True):
        expected = round(granule.size_mb * 1e6) if granule.size_mb else None
        if not path.is_file() or (expected and path.stat().st_size != expected):
            raise RuntimeError("La descarga NISAR está incompleta. Revisa data/00_inbox antes de ingerir.")
        with path.open("rb") as handle:
            if handle.read(8) != HDF5_SIGNATURE:
                raise RuntimeError("El archivo descargado no contiene una cabecera HDF5 válida.")
    return paths
