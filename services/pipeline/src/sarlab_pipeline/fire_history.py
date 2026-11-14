"""Complete MODIS detection counts from ingested FIRMS originals, never burned-area estimates."""
from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from . import settings as S
from .ingest import FIRMS_RE, _write_json, load_catalog


def aggregate(paths: list[Path], start: date, end: date) -> dict:
    covered, seen = set(), set()
    years, months, versions = Counter(), Counter(), set()
    for path in paths:
        match = FIRMS_RE.fullmatch(path.name)
        if not match:
            raise ValueError("El archivo debe conservar el identificador de la consulta FIRMS.")
        first = date.fromisoformat(match["day"])
        covered.update(first + timedelta(days=step) for step in range(int(match["days"])))
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                observed = date.fromisoformat(row["acq_date"])
                if not start <= observed <= end:
                    continue
                fields = ("latitude", "longitude", "acq_date", "acq_time", "satellite")
                identity = tuple(row[key] for key in fields)
                if identity in seen:
                    continue
                seen.add(identity)
                years[observed.year] += 1
                months[observed.month] += 1
                versions.add(row.get("version", "sin especificar"))
    expected = {start + timedelta(days=step) for step in range((end - start).days + 1)}
    if missing := expected - covered:
        raise ValueError(f"Faltan originales para {len(missing)} días; no se publicará una serie incompleta.")
    annual = [{"year": year, "count": years[year]} for year in range(start.year, end.year + 1)]
    return {"start": start.isoformat(), "end": end.isoformat(), "annual": annual,
            "monthly": [{"month": month, "total": months[month],
                         "mean": round(months[month] / len(annual), 2)} for month in range(1, 13)],
            "count": len(seen), "covered_days": len(expected), "versions": sorted(versions)}


def publish(aoi: str) -> dict:
    if aoi != "ayacucho-huanta":
        raise ValueError("Los originales disponibles corresponden a Ayacucho.")
    paths = [S.RAW / row["path"] for row in load_catalog()["items"].values()
             if row.get("source") == "firms" and row.get("product") == "MODIS_SP"]
    result = {"aoi": aoi, **aggregate(paths, date(2001, 1, 1), date(2025, 12, 31)),
              "source": "NASA FIRMS · MODIS Standard Processing", "unit": "detecciones",
              "source_url": "https://firms.modaps.eosdis.nasa.gov/api/area",
              "retrieved_at": datetime.now(UTC).isoformat(),
              "bbox": [-74.4, -13.4, -73.9, -12.8], "originals": len(paths),
              "note": "Cada foco es una detección térmica, no un incendio único ni una hectárea quemada. "
                      "Un evento puede tener varios focos. La cobertura, las nubes y los sensores cambian; "
                      "Aqua se incorpora en 2002. No es una tendencia de área forestal quemada."}
    folder = S.PUBLISHED / "fire-history"
    folder.mkdir(parents=True, exist_ok=True)
    _write_json(folder / f"{aoi}.json", result)
    return result
