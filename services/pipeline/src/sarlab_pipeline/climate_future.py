"""Publish regional climate deltas from Open-Meteo CMIP6 simulations."""
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from math import isfinite
from statistics import mean

import httpx

from .config import load_aois
from .field_evidence import write_json
from .settings import PUBLISHED

SOURCE = "https://climate-api.open-meteo.com/v1/climate"
MODELS = ("EC_Earth3P_HR", "MPI_ESM1_2_XR", "CMCC_CM2_VHR4")
PERIODS = ((1991, 2020), (2041, 2050))
VARIABLES = ("temperature_2m_min", "precipitation_sum")


def monthly(data, start, end):
    first = date(start, 1, 1)
    days = (date(end + 1, 1, 1) - first).days
    dates = [(first + timedelta(days=i)).isoformat() for i in range(days)]
    series = data["daily"]
    if series["time"] != dates or any(len(series[key]) != days for key in VARIABLES):
        raise ValueError("La fuente no devolvió el periodo diario completo")
    samples = defaultdict(list)
    for day, temperature, rain in zip(dates, *(series[k] for k in VARIABLES), strict=True):
        if temperature is None or rain is None or not isfinite(temperature) or not isfinite(rain) or rain < 0:
            raise ValueError("La fuente devolvió valores diarios inválidos")
        samples[day[:7]].append((temperature, rain))
    result = defaultdict(list)
    for key, values in samples.items():
        result[int(key[-2:])].append((mean(t for t, _ in values), sum(r for _, r in values)))
    return {m: (mean(t for t, _ in values), mean(r for _, r in values)) for m, values in result.items()}


def publish(aoi):
    region = load_aois()[aoi]
    west, south, east, north = region.bbox
    results, failures = [], []
    with httpx.Client(timeout=40) as client:
        for model in MODELS:
            try:
                periods, cells = [], []
                for start, end in PERIODS:
                    response = client.get(SOURCE, params={
                        "latitude": (south + north) / 2, "longitude": (west + east) / 2,
                        "models": model, "daily": ",".join(VARIABLES), "timezone": "GMT",
                        "start_date": f"{start}-01-01", "end_date": f"{end}-12-31",
                    })
                    response.raise_for_status()
                    data = response.json()
                    periods.append(monthly(data, start, end))
                    cells.append({k: data[k] for k in ("latitude", "longitude", "elevation")})
                if cells[0] != cells[1]:
                    raise ValueError("La celda cambió entre periodos")
                baseline, future = periods
                results.append({"model": model, "cell": cells[0], "months": {
                    m: {"min_c": round(future[m][0] - baseline[m][0], 2),
                        "rain_pct": round(100 * (future[m][1] / baseline[m][1] - 1), 1)
                        if baseline[m][1] > 0 else None}
                    for m in range(1, 13)
                }})
            except (httpx.HTTPError, KeyError, ValueError, TypeError):
                failures.append(model)
    if len(results) < 2:
        raise ValueError(
            f"Se requieren dos modelos completos. Modelos sin periodo completo: {', '.join(failures)}",
        )
    payload = {"source": SOURCE, "reference": [1991, 2020], "future": [2041, 2050],
               "generated_at": datetime.now(UTC).isoformat(), "models": results, "unavailable": failures}
    write_json(PUBLISHED / "climate-future" / f"{aoi}.json", payload)
    return {"models": [r["model"] for r in results], "unavailable": failures,
            "november": [r["months"][11] for r in results]}
