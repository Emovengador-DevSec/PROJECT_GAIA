"""Línea de comandos: `uv run sarlab <comando>`."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    from .settings import ROOT
    load_dotenv(ROOT / ".env", override=False)
    ap = argparse.ArgumentParser(prog="sarlab", description="Pipeline NISAR de Bailando con los SARs")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="Busca gránulos NISAR sobre una zona configurada")
    s.add_argument("--aoi", required=True); s.add_argument("--product", default="GCOV")
    s.add_argument("--start", required=True); s.add_argument("--end", default=date.today().isoformat())
    s.add_argument("--maturity", default="PROVISIONAL", choices=["PROVISIONAL", "BETA"])
    s.add_argument("--direction", choices=["ASCENDING", "DESCENDING"])
    s.add_argument("--track", type=int, help="Trayectoria relativa para comparar la misma geometría")
    s.add_argument("--frame", type=int, help="Marco de adquisición de ASF")
    s.add_argument("--max-results", type=int, default=1000)
    s.add_argument("--json", action="store_true", help="Muestra metadatos públicos como JSON")
    s.add_argument("--save-catalog", action="store_true",
                   help="Guarda los metadatos públicos en data/catalog")
    s.add_argument("--dates", nargs="+", help="Fechas de adquisición exactas YYYY-MM-DD")
    s.add_argument("--download", action="store_true", help="Descarga a data/00_inbox")
    s.add_argument("--limit", type=int, default=2)

    i = sub.add_parser("inspect", help="Lista las capas de un archivo HDF5")
    i.add_argument("path")

    sub.add_parser("ingest", help="Valida data/00_inbox y mueve a data/01_raw")

    c = sub.add_parser("change", help="Cambio de retrodispersión entre dos gránulos GCOV")
    c.add_argument("--aoi", required=True); c.add_argument("--before", required=True)
    c.add_argument("--after", required=True)
    c.add_argument("--layers", nargs="+", default=["HHHH", "HVHV"], help="Polarizaciones a comparar")
    c.add_argument("--freq", default="frequencyA", choices=["frequencyA", "frequencyB"])

    t = sub.add_parser("timeseries", help="Serie de tiempo de la zona con N gránulos GCOV")
    t.add_argument("--aoi", required=True); t.add_argument("files", nargs="+")
    t.add_argument("--freq", default="frequencyA", choices=["frequencyA", "frequencyB"])

    e = sub.add_parser("exposure", help="Precalcula exposición con WorldPop, WorldCover y lugares OSM reales")
    e.add_argument("--aoi", required=True)
    e.add_argument("--population", type=Path)
    e.add_argument("--population-unit", choices=["people_per_pixel"])
    e.add_argument("--landcover", type=Path)
    e.add_argument("--places", type=Path)
    for source in ("population", "landcover", "places"):
        e.add_argument(f"--{source}-date", help="Fecha de la fuente YYYY-MM-DD")
    e.add_argument("--buffer-m", type=float, default=2000,
                   help="Radio de centros poblados cercanos, en metros")

    a = ap.parse_args(argv)

    if a.cmd == "search":
        from .config import load_aois
        from .sources import nisar
        aois = load_aois()
        if a.aoi not in aois:
            ap.error(f"Zona desconocida: {a.aoi}. Zonas disponibles: {', '.join(aois)}")
        aoi = aois[a.aoi]
        g = nisar.search(aoi.wkt(), date.fromisoformat(a.start), date.fromisoformat(a.end),
                         a.product, a.maturity, a.direction, a.max_results, a.track, a.frame)
        if a.dates:
            wanted_dates = {date.fromisoformat(value).isoformat() for value in a.dates}
            g = [granule for granule in g if granule.start[:10] in wanted_dates]
            missing_dates = wanted_dates - {granule.start[:10] for granule in g}
            if missing_dates:
                missing = ", ".join(sorted(missing_dates))
                ap.error(f"Sin observaciones compatibles en las fechas solicitadas: {missing}")
        catalog = {"aoi_id": a.aoi, "product": a.product, "maturity": a.maturity,
                   "source": "ASF DAAC", "queried_at": datetime.now(UTC).isoformat(),
                   "query": {"start": a.start, "end": a.end, "track": a.track,
                             "direction": a.direction, "frame": a.frame},
                   "granules": [asdict(x) for x in g]}
        if a.save_catalog:
            from .settings import CATALOG
            CATALOG.mkdir(parents=True, exist_ok=True)
            output = CATALOG / f"nisar_{a.aoi}_{a.product.lower()}.json"
            output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        if a.json:
            print(json.dumps(catalog, ensure_ascii=False, indent=2))
        else:
            for x in g:
                size = f"{x.size_mb:,.0f} MB" if x.size_mb else "tamaño no publicado"
                print(f"{x.start}  {x.direction or '-':10} track={x.track} frame={x.frame}  {size}  {x.name}")
            print(f"\n{len(g)} gránulos .h5 encontrados")
        if a.download and g:
            if a.limit < 1:
                ap.error("--limit debe ser mayor que cero.")
            paths = nisar.download(g[: a.limit])
            print("Descargados en data/00_inbox:", *[p.name for p in paths], sep="\n  ")
    elif a.cmd == "inspect":
        from .readers.hdf5_inspect import inspect
        print("\n".join(inspect(a.path)))
    elif a.cmd == "ingest":
        from .ingest import ingest_inbox
        print(json.dumps(ingest_inbox(), ensure_ascii=False, indent=2))
    elif a.cmd == "change":
        from .workflows import change_multi
        r = change_multi(a.aoi, Path(a.before), Path(a.after), tuple(a.layers), a.freq)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif a.cmd == "timeseries":
        from .analysis import timeseries
        r = timeseries(a.aoi, [Path(f) for f in a.files], a.freq)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif a.cmd == "exposure":
        from .exposure import calculate
        try:
            result = calculate(a.aoi, a.population, a.landcover, a.places, a.population_unit,
                               a.population_date, a.landcover_date, a.places_date, a.buffer_m)
        except ValueError as exc:
            ap.error(str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
