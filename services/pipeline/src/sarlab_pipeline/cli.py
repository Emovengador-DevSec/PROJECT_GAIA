"""Línea de comandos: `uv run sarlab <comando>`."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sarlab", description="Pipeline NISAR de Bailando con los SARs")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="Busca gránulos NISAR sobre una zona configurada")
    s.add_argument("--aoi", required=True); s.add_argument("--product", default="GCOV")
    s.add_argument("--start", required=True); s.add_argument("--end", default=date.today().isoformat())
    s.add_argument("--maturity", default="PROVISIONAL", choices=["PROVISIONAL", "BETA"])
    s.add_argument("--direction", choices=["ASCENDING", "DESCENDING"])
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

    a = ap.parse_args(argv)

    if a.cmd == "search":
        from .config import load_aois
        from .sources import nisar
        aoi = load_aois()[a.aoi]
        g = nisar.search(aoi.wkt(), date.fromisoformat(a.start), date.fromisoformat(a.end),
                         a.product, a.maturity, a.direction)
        for x in g:
            print(f"{x.start}  {x.direction or '-':10} track={x.track}  {x.size_mb or 0:,.0f} MB  {x.name}")
        print(f"\n{len(g)} gránulos .h5 encontrados")
        if a.download and g:
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
