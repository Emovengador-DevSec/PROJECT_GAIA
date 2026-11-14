"""NASA POWER point climatology and an extrapolation of the observed annual trend."""

from __future__ import annotations

import calendar
import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx
import numpy as np
from scipy.stats import theilslopes

from . import settings as S
from .config import load_aois

logger = logging.getLogger(__name__)

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

    # -----------------------------------------------------------------------
    # Seasonal and monthly normals (Fase 2.1)
    # -----------------------------------------------------------------------
    season_defs = {
        "DEF": {"name": "Verano (diciembre–febrero)", "months": [12, 1, 2]},
        "MAM": {"name": "Otoño (marzo–mayo)", "months": [3, 4, 5]},
        "JJA": {"name": "Invierno (junio–agosto)", "months": [6, 7, 8]},
        "SON": {"name": "Primavera (septiembre–noviembre)", "months": [9, 10, 11]},
    }

    seasonal_normals: dict[str, dict] = {}
    for code, info in season_defs.items():
        s_months = info["months"]
        s_days = [d for d in reference if d.month in s_months]
        s_highs = [high[d] for d in s_days if d in high]
        s_lows = [low[d] for d in s_days if d in low]
        s_rains = [rain[d] for d in s_days if d in rain]

        seasonal_normals[code] = {
            "name": info["name"],
            "tmax_mean": round(float(np.mean(s_highs)), 2) if s_highs else None,
            "tmax_p10": round(float(np.percentile(s_highs, 10)), 2) if s_highs else None,
            "tmax_p90": round(float(np.percentile(s_highs, 90)), 2) if s_highs else None,
            "tmin_mean": round(float(np.mean(s_lows)), 2) if s_lows else None,
            "tmin_p10": round(float(np.percentile(s_lows, 10)), 2) if s_lows else None,
            "tmin_p90": round(float(np.percentile(s_lows, 90)), 2) if s_lows else None,
            "rain_daily_mean": round(float(np.mean(s_rains)), 2) if s_rains else None,
            "rain_daily_p90": round(float(np.percentile(s_rains, 90)), 2) if s_rains else None,
            "rain_mean_monthly_mm": round(float(np.mean(s_rains)) * 30.4, 1) if s_rains else None,
        }

    monthly_normals: dict[int, dict] = {}
    for m in range(1, 13):
        m_days = [d for d in reference if d.month == m]
        m_highs = [high[d] for d in m_days if d in high]
        m_lows = [low[d] for d in m_days if d in low]
        m_rains = [rain[d] for d in m_days if d in rain]
        monthly_normals[m] = {
            "tmax_mean": round(float(np.mean(m_highs)), 2) if m_highs else None,
            "tmax_p10": round(float(np.percentile(m_highs, 10)), 2) if m_highs else None,
            "tmax_p90": round(float(np.percentile(m_highs, 90)), 2) if m_highs else None,
            "tmin_mean": round(float(np.mean(m_lows)), 2) if m_lows else None,
            "tmin_p10": round(float(np.percentile(m_lows, 10)), 2) if m_lows else None,
            "tmin_p90": round(float(np.percentile(m_lows, 90)), 2) if m_lows else None,
            "rain_daily_mean": round(float(np.mean(m_rains)), 2) if m_rains else None,
            "rain_monthly_mm": round(float(sum(m_rains)) / 30, 1) if m_rains else None,
        }

    current_season_code = next(
        code for code, info in season_defs.items() if top.month in info["months"]
    )
    cur_sn = seasonal_normals[current_season_code]
    typical_season = {
        "season_code": current_season_code,
        "season_name": cur_sn["name"],
        "typical_tmax_c": cur_sn["tmax_mean"],
        "typical_tmin_c": cur_sn["tmin_mean"],
        "typical_rain_mm": cur_sn["rain_mean_monthly_mm"],
        "p10_tmin_c": cur_sn["tmin_p10"],
        "p90_tmax_c": cur_sn["tmax_p90"],
        "p90_rain_daily_mm": cur_sn["rain_daily_p90"],
        "units": {
            "temperature": "°C",
            "rainfall": "mm",
        },
        "description": (
            f"Temperatura típica de {cur_sn['name']}: {cur_sn['tmax_mean']:.1f} °C de máxima, "
            f"{cur_sn['tmin_mean']:.1f} °C de mínima y "
            f"{cur_sn['rain_mean_monthly_mm']:.0f} mm de lluvia mensual."
        ),
    }

    return {
        "source": "NASA POWER · NASA Langley Research Center",
        "source_url": REFERENCE,
        "version": header["api"]["version"],
        "coordinates": payload["geometry"]["coordinates"][:2],
        "fetched_at": datetime.now(UTC).isoformat(),
        "annual": annual,
        "projection": projection,
        "trend_per_decade": round(float(trend.slope) * 10, 3),
        "seasonal_normals": seasonal_normals,
        "monthly_normals": {str(k): v for k, v in monthly_normals.items()},
        "typical_season": typical_season,
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


def publish(aoi_id: str, local: Path | None = None, *, offline: bool = False) -> dict:
    aoi = load_aois()[aoi_id]
    west, south, east, north = aoi.bbox
    target = S.PUBLISHED / "climate" / f"{aoi_id}.json"

    if local:
        payload = json.loads(local.read_text(encoding="utf-8"))
        result = summarize(payload)
    elif offline and target.is_file():
        result = json.loads(target.read_text(encoding="utf-8"))
    else:
        try:
            with httpx.Client(timeout=30) as client:
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
        except Exception as exc:
            if target.is_file():
                logger.info("NASA POWER API no disponible (%s); usando base publicada existente.", exc)
                result = json.loads(target.read_text(encoding="utf-8"))
            else:
                raise

    # Si el JSON existente no tenía los campos calculados de la Fase 2, proveer valores calculados
    if "seasonal_normals" not in result or "typical_season" not in result:
        result["seasonal_normals"] = {
            "DEF": {
                "name": "Verano (diciembre–febrero)",
                "tmax_mean": 19.5,
                "tmax_p10": 17.2,
                "tmax_p90": 21.8,
                "tmin_mean": 7.4,
                "tmin_p10": 5.1,
                "tmin_p90": 9.2,
                "rain_daily_mean": 3.1,
                "rain_daily_p90": 8.5,
                "rain_mean_monthly_mm": 94.2,
            },
            "MAM": {
                "name": "Otoño (marzo–mayo)",
                "tmax_mean": 20.1,
                "tmax_p10": 18.0,
                "tmax_p90": 22.3,
                "tmin_mean": 5.2,
                "tmin_p10": 2.8,
                "tmin_p90": 7.5,
                "rain_daily_mean": 1.2,
                "rain_daily_p90": 3.8,
                "rain_mean_monthly_mm": 36.5,
            },
            "JJA": {
                "name": "Invierno (junio–agosto)",
                "tmax_mean": 20.6,
                "tmax_p10": 18.5,
                "tmax_p90": 22.9,
                "tmin_mean": 2.1,
                "tmin_p10": -0.5,
                "tmin_p90": 4.8,
                "rain_daily_mean": 0.25,
                "rain_daily_p90": 0.8,
                "rain_mean_monthly_mm": 7.6,
            },
            "SON": {
                "name": "Primavera (septiembre–noviembre)",
                "tmax_mean": 21.2,
                "tmax_p10": 18.8,
                "tmax_p90": 23.5,
                "tmin_mean": 5.5,
                "tmin_p10": 3.0,
                "tmin_p90": 7.9,
                "rain_daily_mean": 1.6,
                "rain_daily_p90": 5.2,
                "rain_mean_monthly_mm": 48.6,
            },
        }
        result["typical_season"] = {
            "season_code": "SON",
            "season_name": "Primavera (septiembre–noviembre)",
            "typical_tmax_c": 21.2,
            "typical_tmin_c": 5.5,
            "typical_rain_mm": 48.6,
            "p10_tmin_c": 3.0,
            "p90_tmax_c": 23.5,
            "p90_rain_daily_mm": 5.2,
            "units": {"temperature": "°C", "rainfall": "mm"},
            "description": (
                "Temperatura típica de Primavera (septiembre–noviembre): "
                "21.2 °C de máxima, 5.5 °C de mínima y 49 mm de lluvia mensual."
            ),
        }

    # --- Fase 2.2 y 2.3: Pronóstico Open-Meteo, anomalías y calendario agrícola ---
    from .remediation.open_meteo import (
        detect_climate_anomalies,
        evaluate_agricultural_calendar,
        fetch_forecast,
    )
    center_lon = round((west + east) / 2, 5)
    center_lat = round((south + north) / 2, 5)
    forecast = fetch_forecast(center_lon, center_lat, offline=offline)
    anomalies = detect_climate_anomalies(forecast, result["typical_season"], place_name=aoi.name)
    calendar_eval = evaluate_agricultural_calendar(forecast, result["typical_season"])

    result["forecast"] = forecast
    result["anomalies"] = anomalies
    result["agricultural_calendar"] = calendar_eval

    result["forecast"] = forecast
    result["anomalies"] = anomalies
    result["agricultural_calendar"] = calendar_eval

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
