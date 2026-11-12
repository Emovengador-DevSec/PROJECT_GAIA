"""Búsqueda y descarga de productos NISAR en ASF DAAC.

Verificado en la documentación de ASF (nov. 2026):
- asf_search: dataset='NISAR', processingLevel='GCOV' | 'GUNW' | 'GOFF' | 'GSLC' | 'SME2'.
- Madurez: dataMaturity='PROVISIONAL' (calibrado) o 'BETA' (precalibración).
- earthaccess short_name: 'NISAR_L2_GCOV_PROVISIONAL_V1' (y equivalentes).
- Cada búsqueda devuelve también archivos QA_STATS: se filtran por extensión .h5.
Revisa https://nisar-docs.asf.alaska.edu/asf-search si cambia la API.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..settings import INBOX, earthdata_token

PRODUCTS = {"GCOV", "GUNW", "GOFF", "GSLC", "SME2"}


@dataclass
class Granule:
    name: str
    url: str
    start: str
    direction: str | None
    track: int | None
    size_mb: float | None


def search(wkt: str, start: date, end: date, product: str = "GCOV",
           maturity: str = "PROVISIONAL", direction: str | None = None,
           max_results: int = 100) -> list[Granule]:
    """Busca gránulos NISAR que intersectan la zona. Requiere `asf_search` instalado."""
    import asf_search as asf  # import tardío: solo se necesita al buscar

    if product not in PRODUCTS:
        raise ValueError(f"Producto no soportado: {product}")
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
        if not url.endswith(".h5"):
            continue  # descarta QA_STATS y auxiliares
        granules.append(Granule(
            name=props.get("fileID") or props.get("sceneName") or Path(url).stem,
            url=url,
            start=props.get("startTime", ""),
            direction=props.get("flightDirection"),
            track=props.get("pathNumber"),
            size_mb=(props.get("bytes") or 0) / 1e6 or None,
        ))
    return sorted(granules, key=lambda g: g.start)


def download(granules: list[Granule], dest: Path = INBOX, processes: int = 2) -> list[Path]:
    """Descarga a data/00_inbox/. Luego `sarlab ingest` los valida y mueve a 01_raw."""
    import asf_search as asf

    token = earthdata_token()
    if not token:
        raise RuntimeError("Falta EARTHDATA_TOKEN en el entorno (.env). Créalo en urs.earthdata.nasa.gov.")
    session = asf.ASFSession().auth_with_token(token)
    dest.mkdir(parents=True, exist_ok=True)
    asf.download_urls([g.url for g in granules], str(dest), session=session, processes=processes)
    return [dest / Path(g.url).name for g in granules]
