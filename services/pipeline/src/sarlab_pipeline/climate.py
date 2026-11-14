"""NASA POWER point climatology and an extrapolation of the observed annual trend."""

from __future__ import annotations

import calendar
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx
import numpy as np
from scipy.stats import theilslopes

from . import settings as S
from .config import load_aois

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
REFERENCE = "https://power.larc.nasa.gov/docs/referencing/"
VARIABLES = ["T2M_MAX", "T2M_MIN", "PRECTOTCORR"]


def summarize(payload: dict) -> dict:
    header = payload["header"]
    values = payload["properties"]["parameter"]
    missing = header["fill_value"]
    valid = [
        {
            date.fromisoformat(key): value
            for key, value in values[name].items()
            if np.isfinite(value) and value != missing
        }
        for name in VARIABLES
    ]
    high, low, rain = valid
    if not high or not low or not rain:
        raise ValueError("NASA POWER no devolvió las tres variables solicitadas.")
    today = datetime.now(UTC).date()
    days = sorted(day for day in high if day <= today)
    top = days[-1]
    reference = [day for day in days if 1991 <= day.year <= 2020]
    wet_reference = {day: value for day, value in rain.items() if 1990 <= day.year <= 2020}
    if len(reference) < 10_000:
        raise ValueError("La climatología 1991–2020 no tiene suficiente cobertura.")

    def seasonal_day(day: date) -> int:
        return day.replace(year=2000).timetuple().tm_yday

    by_season = {}
    for number in range(1, 367):
        sample = [
            high[day]
            for day in reference
            if min(abs(seasonal_day(day) - number), 366 - abs(seasonal_day(day) - number)) <= 7
        ]
        by_season[number] = float(np.percentile(sample, 90))
    heat_dates = set()
    run: list[date] = []
    current_days = 0
    for day in days:
        if day > top - timedelta(days=369):
            if run and day - run[-1] != timedelta(days=1):
                run.clear()
            if high[day] > by_season.get(seasonal_day(day), float("inf")):
                run.append(day)
                if len(run) >= 3:
                    heat_dates.update(run[-3:])
            else:
                run.clear()
            if day == top:
                current_days = len(run)

    def rain_total(end: date, data: dict) -> float | None:
        window = [data.get(end - timedelta(days=offset)) for offset in range(30)]
        return float(sum(window)) if all(value is not None for value in window) else None

    anchors = [
        top.replace(year=year, day=28 if top.month == 2 and top.day == 29 else top.day)
        for year in range(1991, 2021)
    ]
    normals = [value for day in anchors if (value := rain_total(day, wet_reference)) is not None]
    observed_rain = rain_total(top, rain)
    normal = float(np.mean(normals)) if len(normals) >= 25 else None
    annual = []
    for year in range(1981, today.year):
        year_days = [day for day in days if day.year == year and day in low and day in rain]
        if len(year_days) == 365 + calendar.isleap(year):
            annual.append(
                {
                    "year": year,
                    "temperature": round(
                        float(
                            np.mean(
                                [(high[day] + low[day]) / 2 for day in year_days],
                            )
                        ),
                        3,
                    ),
                    "rain_mm": round(sum(rain[day] for day in year_days), 1),
                }
            )
    if len(annual) < 30:
        raise ValueError("NASA POWER no devolvió suficientes años completos.")
    years = np.array([row["year"] for row in annual])
    temps = np.array([row["temperature"] for row in annual])
    trend = theilslopes(temps, years, method="joint")
    anchor = float(np.median(years))
    center = float(trend.intercept + trend.slope * anchor)
    projection = [
        {
            "year": year,
            "temperature": round(center + trend.slope * (year - anchor), 3),
            "low": round(center + trend.low_slope * (year - anchor), 3),
            "high": round(center + trend.high_slope * (year - anchor), 3),
        }
        for year in range(int(years[-1]), 2036)
    ]
    last_year_hot = sum(day > top - timedelta(days=365) for day in heat_dates)
    return {
        "source": "NASA POWER · NASA Langley Research Center",
        "source_url": REFERENCE,
        "version": header["api"]["version"],
        "coordinates": payload["geometry"]["coordinates"][:2],
        "fetched_at": datetime.now(UTC).isoformat(),
        "annual": annual,
        "projection": projection,
        "trend_per_decade": round(float(trend.slope) * 10, 3),
        "current": {
            "date": top.isoformat(),
            "max_c": high[top],
            "min_c": low.get(top),
            "heat_days": current_days,
            "hot_last_year": last_year_hot,
            "rain_mm": observed_rain,
            "normal_rain_mm": normal,
            "rain_ratio": observed_rain / normal if observed_rain is not None and normal else None,
        },
    }


def publish(aoi_id: str, local: Path | None = None) -> dict:
    aoi = load_aois()[aoi_id]
    west, south, east, north = aoi.bbox
    if local:
        payload = json.loads(local.read_text(encoding="utf-8"))
    else:
        with httpx.Client(timeout=60) as client:
            response = client.get(
                URL,
                params={
                    "parameters": ",".join(VARIABLES),
                    "community": "AG",
                    "longitude": round((west + east) / 2, 5),
                    "latitude": round((south + north) / 2, 5),
                    "start": "19810101",
                    "end": date.today().strftime("%Y%m%d"),
                    "format": "JSON",
                    "time-standard": "UTC",
                },
            )
            response.raise_for_status()
            payload = response.json()
    result = summarize(payload)
    target = S.PUBLISHED / "climate" / f"{aoi_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=target.parent, delete=False, mode="w", encoding="utf-8") as saved:
        temporary = Path(saved.name)
        json.dump(result, saved, ensure_ascii=False, allow_nan=False)
    try:
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return result
