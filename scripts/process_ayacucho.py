"""Procesa las dos observaciones GCOV de Ayacucho seleccionadas en ASF."""
from __future__ import annotations

import json
from datetime import date

from dotenv import load_dotenv

from sarlab_pipeline import settings
from sarlab_pipeline.analysis import timeseries
from sarlab_pipeline.config import load_aois
from sarlab_pipeline.exposure import calculate
from sarlab_pipeline.ingest import ingest_inbox, load_catalog
from sarlab_pipeline.readers.hdf5_inspect import inspect
from sarlab_pipeline.sources.nisar import download, search
from sarlab_pipeline.workflows import change_multi

AOI = "ayacucho-huanta"
DATES = {"2026-06-19", "2026-10-05"}


def main() -> None:
    load_dotenv(settings.ROOT / ".env", override=False)
    if not settings.earthdata_token():
        raise SystemExit("Configura EARTHDATA_TOKEN en el entorno de GAIA para iniciar la descarga.")
    zone = load_aois()[AOI]
    results = search(zone.wkt(), date(2026, 6, 19), date(2026, 10, 6),
                     direction="ASCENDING", track=75, frame=171)
    granules = [item for item in results
                if item.start[:10] in DATES and {"HH", "HV"} <= set(item.polarizations)]
    if len(granules) != 2 or {item.start[:10] for item in granules} != DATES:
        raise SystemExit("ASF no devolvió exactamente las dos fechas compatibles seleccionadas.")
    if any(item.size_mb is None for item in granules) or sum(item.size_mb or 0 for item in granules) > 5000:
        raise SystemExit("Los tamaños de ASF requieren revisión antes de descargar.")

    names = [item.url.rsplit("/", 1)[-1] for item in granules]
    existing = load_catalog()["items"]
    pending = [item for item, name in zip(granules, names, strict=True)
               if name not in existing or not (settings.RAW / existing[name]["path"]).is_file()]
    if pending:
        download(pending)
        print(json.dumps(ingest_inbox(), ensure_ascii=False, indent=2))
    catalog = load_catalog()["items"]
    if any(name not in catalog for name in names):
        raise SystemExit("La ingesta no registró ambos archivos. Revisa los motivos en data/99_quarantine.")
    paths = [settings.RAW / catalog[name]["path"] for name in names]
    inspected = []
    for path in paths:
        inspected.extend([path.name, *inspect(path)])
    (settings.CATALOG / "ayacucho-huanta-inspect.txt").write_text("\n".join(inspected), encoding="utf-8")
    change = change_multi(AOI, *paths)
    series = timeseries(AOI, paths)
    print(json.dumps({"change": change, "series": series}, ensure_ascii=False, indent=2))

    context = settings.INTERIM / AOI
    population = context / "worldpop.tif"
    landcover = context / "worldcover.tif"
    if population.is_file() and landcover.is_file():
        result = calculate(AOI, population, landcover, population_unit="people_per_pixel",
                           population_date="2025-01-01", landcover_date="2021-01-01")
        print(f"Exposición calculada para {len(result['alerts'])} polígonos.")


if __name__ == "__main__":
    main()
