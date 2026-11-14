"""Open-Meteo client, climate anomaly detector, and smart agricultural calendar (Fase 2).

Uses Open-Meteo public API (no key required for non-commercial use).
Compares forecast against NASA POWER 45-year climatological normals.
Rules and crops defined in config/nbs/climate_alerts.yaml and config/nbs/crops.yaml.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import yaml

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
ROOT = Path(__file__).resolve().parents[5]
CONFIG_NBS = ROOT / "config" / "nbs"


def _load_yaml(path: Path) -> dict:
    if path.is_file():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


def fetch_forecast(
    lon: float,
    lat: float,
    *,
    days: int = 14,
    timeout: float = 6.0,
    offline: bool = False,
    cache_path: Path | None = None,
) -> dict[str, Any] | None:
    """Fetch 7–14 day daily forecast from Open-Meteo with local cached fallback."""
    cache = cache_path or (ROOT / "data" / "catalog" / "live" / "forecast_ayacucho.json")

    if not offline:
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "soil_moisture_0_to_10cm_mean",
            ],
            "timezone": "America/Lima",
            "forecast_days": min(max(days, 7), 16),
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(OPEN_METEO_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return {
                    "fetched_at": datetime.now(tz=UTC).isoformat(),
                    "source": "Open-Meteo API",
                    "source_url": "https://open-meteo.com/",
                    "status": "live",
                    "daily": data.get("daily", {}),
                }
        except Exception as exc:
            logger.warning("Open-Meteo forecast live fetch unavailable: %s", exc)

    # Fallback to cache if available
    if cache.is_file():
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            cached["status"] = "cached"
            return cached
        except Exception:
            pass

    return None


def detect_climate_anomalies(
    forecast: dict[str, Any] | None,
    typical_season: dict[str, Any],
    place_name: str = "Ayacucho · Huamanga y Huanta",
    config_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Detect heat, frost, and heavy rain anomalies by comparing forecast to seasonal normals.

    Returns a list of anomaly alerts conforming to GAIA Alerta schema.
    """
    if not forecast or not forecast.get("daily"):
        return []

    cfg = _load_yaml(config_path or (CONFIG_NBS / "climate_alerts.yaml"))
    thresholds = cfg.get("thresholds", {})
    daily = forecast["daily"]
    times = daily.get("time", [])
    tmaxs = daily.get("temperature_2m_max", [])
    tmins = daily.get("temperature_2m_min", [])
    rains = daily.get("precipitation_sum", [])

    anomalies: list[dict[str, Any]] = []

    p90_tmax = typical_season.get("p90_tmax_c", 22.0)
    p10_tmin = typical_season.get("p10_tmin_c", 2.0)
    p90_rain = typical_season.get("p90_rain_daily_mm", 15.0)
    season_name = typical_season.get("season_name", "Estación actual")

    for i, day_str in enumerate(times):
        tmax = tmaxs[i] if i < len(tmaxs) else None
        tmin = tmins[i] if i < len(tmins) else None
        rain = rains[i] if i < len(rains) else None

        # 1. Extreme frost for livestock (< -3 °C)
        if tmin is not None and tmin <= thresholds.get("extreme_frost", {}).get("temp_min_c", -3.0):
            anomalies.append({
                "id": f"clm_extreme_frost_{day_str}",
                "kind": "climate_anomaly",
                "source": "Clima · Open-Meteo / NASA POWER",
                "source_kind": "complementary",
                "title": f"Alerta de helada severa para ganado: {tmin:.1f} °C",
                "place": place_name,
                "date": f"{day_str}T06:00:00Z",
                "level": "alto",
                "confidence": "pronóstico meteorológico",
                "metrics": {"tmin_c": tmin, "normal_p10_c": p10_tmin},
                "note": (
                    f"Pronóstico de mínima de {tmin:.1f} °C en zonas altas. "
                    "Riesgo crítico de mortandad de crías de alpacas y ovinos. Resguardar en cobertizos."
                ),
                "source_url": "https://open-meteo.com/",
            })

        # 2. Frost risk (tmin < 0 °C or tmin < P10)
        elif tmin is not None and (
            tmin < thresholds.get("frost_puna", {}).get("temp_min_c", 0.0) or tmin < p10_tmin
        ):
            anomalies.append({
                "id": f"clm_frost_{day_str}",
                "kind": "climate_anomaly",
                "source": "Clima · Open-Meteo / NASA POWER",
                "source_kind": "complementary",
                "title": f"Aviso de helada: mínima de {tmin:.1f} °C",
                "place": place_name,
                "date": f"{day_str}T06:00:00Z",
                "level": "alto" if tmin < 0 else "medio",
                "confidence": "pronóstico meteorológico",
                "metrics": {"tmin_c": tmin, "normal_p10_c": p10_tmin},
                "note": (
                    f"Temperatura mínima ({tmin:.1f} °C) por debajo del percentil 10 histórico "
                    f"de {season_name} ({p10_tmin:.1f} °C). Riesgo de daño a flores y brotes tiernos."
                ),
                "source_url": "https://open-meteo.com/",
            })

        # 3. Heat anomaly (tmax > P90)
        if tmax is not None and tmax > p90_tmax:
            anomalies.append({
                "id": f"clm_heat_{day_str}",
                "kind": "climate_anomaly",
                "source": "Clima · Open-Meteo / NASA POWER",
                "source_kind": "complementary",
                "title": f"Aviso de calor anómalo: {tmax:.1f} °C",
                "place": place_name,
                "date": f"{day_str}T14:00:00Z",
                "level": "medio",
                "confidence": "pronóstico meteorológico",
                "metrics": {"tmax_c": tmax, "normal_p90_c": p90_tmax},
                "note": (
                    f"Temperatura máxima pronosticada ({tmax:.1f} °C) supera el percentil 90 histórico "
                    f"de {season_name} ({p90_tmax:.1f} °C). Mayor evapotranspiración y estrés de plántulas."
                ),
                "source_url": "https://open-meteo.com/",
            })

        # 4. Heavy rainfall
        heavy_thresh = thresholds.get("heavy_rainfall", {}).get("daily_mm_threshold", 20.0)
        if rain is not None and (rain >= heavy_thresh or rain > p90_rain):
            anomalies.append({
                "id": f"clm_rain_{day_str}",
                "kind": "climate_anomaly",
                "source": "Clima · Open-Meteo / NASA POWER",
                "source_kind": "complementary",
                "title": f"Aviso de lluvia intensa: {rain:.1f} mm/día",
                "place": place_name,
                "date": f"{day_str}T18:00:00Z",
                "level": "medio",
                "confidence": "pronóstico meteorológico",
                "metrics": {"rain_mm": rain, "normal_p90_mm": p90_rain},
                "note": (
                    f"Precipitación diaria pronosticada ({rain:.1f} mm) supera la normal de {season_name}. "
                    "Precaución en laderas agrícolas con pendiente > 15° por escorrentía superficial."
                ),
                "source_url": "https://open-meteo.com/",
            })

    return anomalies


def evaluate_agricultural_calendar(
    forecast: dict[str, Any] | None,
    typical_season: dict[str, Any],
    crops_config_path: Path | None = None,
    current_date: date | None = None,
) -> dict[str, Any]:
    """Evaluate sowing windows and risk warnings for Andean crops and livestock.

    Crops evaluated: Papa, Maíz, Quinua, Habas.
    """
    cfg = _load_yaml(crops_config_path or (CONFIG_NBS / "crops.yaml"))
    crops = cfg.get("crops", [])
    livestock_cfg = cfg.get("livestock", {})

    today = current_date or date.today()
    current_month = today.month

    daily = (forecast or {}).get("daily", {})
    times = daily.get("time", [])
    tmins = daily.get("temperature_2m_min", [])
    tmaxs = daily.get("temperature_2m_max", [])
    rains = daily.get("precipitation_sum", [])
    moistures = daily.get("soil_moisture_0_to_10cm_mean", [])

    # Calculate 7-day outlook averages
    outlook_days = min(7, len(times))
    if outlook_days > 0:
        avg_tmin = float(sum(tmins[:outlook_days]) / outlook_days) if tmins else None
        avg_tmax = float(sum(tmaxs[:outlook_days]) / outlook_days) if tmaxs else None
        total_rain_7d = float(sum(rains[:outlook_days])) if rains else None
        avg_moisture = float(sum(moistures[:outlook_days]) / outlook_days) if moistures else None
        has_frost = any(t <= 0.0 for t in tmins[:outlook_days] if t is not None)
        has_extreme_frost = any(t <= -3.0 for t in tmins[:outlook_days] if t is not None)
    else:
        avg_tmin = typical_season.get("typical_tmin_c", 6.0)
        avg_tmax = typical_season.get("typical_tmax_c", 18.0)
        total_rain_7d = typical_season.get("typical_rain_mm", 30.0) / 4.0
        avg_moisture = 0.20
        has_frost = False
        has_extreme_frost = False

    evaluated_crops = []

    for crop in crops:
        sowing_months = crop.get("sowing_months", [])
        is_sowing_season = current_month in sowing_months
        min_temp = crop.get("min_temp_c", 4.0)
        frost_sensitive = crop.get("frost_sensitive", True)
        min_moisture = crop.get("min_soil_moisture", 0.15)
        guidance = crop.get("guidance", {})

        # Determine suitability
        status = "favorable"
        reasons = []

        if not is_sowing_season:
            status = "fuera_de_temporada"
            reasons.append("Mes fuera de la ventana tradicional de siembra.")
        elif frost_sensitive and has_frost:
            status = "precaucion"
            reasons.append(guidance.get("frost_warning", "Riesgo de helada en los próximos 7 días."))
        elif avg_moisture is not None and avg_moisture < min_moisture:
            status = "precaucion"
            reasons.append(guidance.get("drought_warning", "Humedad del suelo baja para siembra."))
        elif avg_tmin is not None and avg_tmin < min_temp:
            status = "precaucion"
            reasons.append(f"Temperatura mínima ({avg_tmin:.1f} °C) inferior a la requerida ({min_temp} °C).")
        else:
            status = "favorable"
            # Formulate suggested window
            end_window = today + timedelta(days=outlook_days)
            reasons.append(
                f"Condiciones favorables para siembra entre el {today.day} y el {end_window.day} "
                f"de {_month_name(today.month)}."
            )

        months_str = ", ".join(_month_name(m) for m in sowing_months)
        evaluated_crops.append({
            "id": crop.get("id"),
            "name": crop.get("name"),
            "scientific": crop.get("scientific"),
            "altitude_m": crop.get("altitude_m"),
            "status": status,
            "sowing_season_months": months_str,
            "guidance": reasons[0] if reasons else guidance.get("favorable", ""),
            "factors": {
                "avg_tmin_c": round(avg_tmin, 1) if avg_tmin is not None else None,
                "avg_tmax_c": round(avg_tmax, 1) if avg_tmax is not None else None,
                "rain_7d_mm": round(total_rain_7d, 1) if total_rain_7d is not None else None,
                "soil_moisture_m3m3": round(avg_moisture, 3) if avg_moisture is not None else None,
            },
        })

    # Livestock guidance
    livestock_status = {
        "name": livestock_cfg.get("name", "Ganado altoandino"),
        "altitude_m": livestock_cfg.get("altitude_m", [3800, 4800]),
        "status": "alerta" if has_extreme_frost else "normal",
        "guidance": (
            livestock_cfg.get("guidance", {}).get("frost_warning")
            if has_extreme_frost
            else "Condiciones normales de pastoreo en puna; mantener cobertizos limpios."
        ),
    }

    return {
        "evaluated_at": today.isoformat(),
        "season": typical_season.get("season_name", ""),
        "outlook_days": outlook_days,
        "crops": evaluated_crops,
        "livestock": livestock_status,
        "promoter_note": (
            "El saber local manda. Esta herramienta sugiere ventanas con datos satelitales y meteorológicos; "
            "cada comunidad conserva su fecha tradicional."
        ),
    }


def _month_name(m: int) -> str:
    names = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    return names[m] if 1 <= m <= 12 else str(m)
