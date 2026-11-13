"""Proyección descriptiva de retrodispersión, exclusivamente con observaciones NISAR."""

import math
import statistics
from datetime import UTC, datetime, timedelta

from scipy.stats import theilslopes


def project(series: dict, polarization: str) -> dict:
    observations = {}
    for sample in series.get("samples", []):
        stats = sample.get(polarization)
        if not isinstance(stats, dict):
            continue
        try:
            value = float(stats["median_db"])
            date = datetime.fromisoformat(sample["date"]).replace(tzinfo=UTC)
            if math.isfinite(value):
                observations[date] = value
        except (KeyError, TypeError, ValueError):
            continue
    rows = sorted(observations.items())
    base = {
        "method": "Theil–Sen",
        "unit": "dB",
        "polarization": polarization,
        "label": "Proyección si la tendencia sigue igual — no es una predicción",
        "dates": len(rows),
        "horizon_days": 12,
        "confidence": 0.95,
        "scope": "Retrodispersión NISAR de la zona; no aplicable a sismos.",
        "projection": [],
    }
    if len(rows) < 4:
        return {
            **base,
            "status": "insufficient",
            "message": "Se necesitan al menos cuatro fechas NISAR distintas con datos válidos.",
        }
    origin = rows[0][0]
    xs = [(date - origin).total_seconds() / 86400 for date, _ in rows]
    ys = [value for _, value in rows]
    fit = theilslopes(ys, xs, alpha=0.95, method="joint")
    residuals = [y - (fit.intercept + fit.slope * x) for x, y in zip(xs, ys, strict=True)]
    residual_center = statistics.median(residuals)
    spread = 1.4826 * statistics.median(abs(r - residual_center) for r in residuals)
    last_x = xs[-1]
    last_fit = float(fit.intercept + fit.slope * last_x)
    points = []
    for days in (0, 3, 6, 9, 12):
        points.append(
            {
                "date": (rows[-1][0] + timedelta(days=days)).date().isoformat(),
                "value": round(last_fit + float(fit.slope) * days, 3),
                "low": round(last_fit + float(fit.low_slope) * days - 1.96 * spread, 3),
                "high": round(last_fit + float(fit.high_slope) * days + 1.96 * spread, 3),
            }
        )
    return {
        **base,
        "status": "ok",
        "slope_db_day": float(fit.slope),
        "projection": points,
        "uncertainty": ("Intervalo de pendiente Theil–Sen al 95 % y dispersión residual robusta. "
                        "No es una probabilidad de desastre."),
    }
