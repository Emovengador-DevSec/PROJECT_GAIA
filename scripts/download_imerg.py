"""Download three original IMERG Late days from NASA CMR into the ingestion inbox."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv

from sarlab_pipeline import settings as S


def download(start: date) -> list[Path]:
    load_dotenv(S.ROOT / ".env", override=False)
    token = S.earthdata_token()
    if not token:
        raise ValueError("Falta EARTHDATA_TOKEN en el servidor.")
    end = start + timedelta(days=2)
    with httpx.Client(timeout=90, follow_redirects=True) as client:
        response = client.get("https://cmr.earthdata.nasa.gov/search/granules.json", params={
            "short_name": "GPM_3IMERGDL", "version": "07", "page_size": 10,
            "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z",
        })
        response.raise_for_status()
        rows = response.json()["feed"]["entry"]
        if len(rows) != 3 or sum(float(row["granule_size"]) for row in rows) > 200:
            raise ValueError("Se requieren tres originales de menos de 200 MB en total.")
        S.INBOX.mkdir(parents=True, exist_ok=True)
        paths = []
        for row in rows:
            name = row["producer_granule_id"]
            links = [link["href"] for link in row["links"]
                     if link.get("rel", "").endswith("/data#") and link["href"].endswith(".nc4")]
            if len(links) != 1 or urlsplit(links[0]).hostname != "data.gesdisc.earthdata.nasa.gov":
                raise ValueError("El catálogo no ofrece un único original en el archivo oficial de NASA.")
            target = S.INBOX / Path(name).name
            partial = target.with_suffix(".partial")
            try:
                with client.stream("GET", links[0], headers={"Authorization": f"Bearer {token}"}) as stream:
                    if stream.status_code in (401, 403):
                        raise ValueError(
                            "Earthdata no autorizó GES DISC. Revisa el acceso y sus condiciones.")
                    stream.raise_for_status()
                    size = 0
                    with partial.open("wb") as handle:
                        for chunk in stream.iter_bytes():
                            size += len(chunk)
                            if size > 70_000_000:
                                raise ValueError("El original supera el límite de 70 MB por archivo.")
                            handle.write(chunk)
                with partial.open("rb") as handle:
                    if handle.read(8) != b"\x89HDF\r\n\x1a\n":
                        raise ValueError("La respuesta no es un original NetCDF4/HDF5.")
                partial.replace(target)
                print(f"{name} · {size} bytes", flush=True)
                paths.append(target)
            finally:
                partial.unlink(missing_ok=True)
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    download(parser.parse_args().start)
