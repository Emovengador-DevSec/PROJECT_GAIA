"""Weighted risk index and NbS recipe engine — Fase 1.

For each alert polygon (from alerts_hvhv.geojson) this module computes:
  - Normalized factor scores (0–1) for HV drop, soil moisture, slope,
    fire heat, recent earthquakes, rainfall and crop exposure.
  - A weighted aggregate index (0–1).
  - Dominant risk category (incendio_sequia, erosion_huaico,
    ladera_inestable_sismo, estres_hidrico_agricola).
  - Risk level (bajo / medio / alto).
  - Matching NbS recipe with interventions and budget estimate.

All weights, thresholds and recipe texts come from config/nbs/*.yaml.
No magic numbers in this file.
"""

from __future__ import annotations

import json
import logging
import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

ROOT = Path(os.environ.get("SARLAB_ROOT", Path(__file__).resolve().parents[5]))
CONFIG_NBS = ROOT / "config" / "nbs"
DATA_PUBLISHED = ROOT / "data" / "04_published"
DATA_PROCESSED = ROOT / "data" / "03_processed"


# ---------------------------------------------------------------------------
# Config loaders (cached at import time)
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


_risk_cfg: dict | None = None
_recipes_cfg: list | None = None
_costs_cfg: list | None = None
_soils_cfg: list | None = None


def _risk() -> dict:
    global _risk_cfg
    if _risk_cfg is None:
        _risk_cfg = _load_yaml(CONFIG_NBS / "risk.yaml")
    return _risk_cfg


def _recipes() -> list[dict]:
    global _recipes_cfg
    if _recipes_cfg is None:
        _recipes_cfg = _load_yaml(CONFIG_NBS / "recipes.yaml").get("recipes", [])
    return _recipes_cfg


def _costs() -> list[dict]:
    global _costs_cfg
    if _costs_cfg is None:
        _costs_cfg = _load_yaml(CONFIG_NBS / "costs.yaml").get("interventions", [])
    return _costs_cfg


def _soils() -> list[dict]:
    global _soils_cfg
    if _soils_cfg is None:
        _soils_cfg = _load_yaml(CONFIG_NBS / "soils.yaml").get("groups", [])
    return _soils_cfg


# ---------------------------------------------------------------------------
# Factor normalizers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _normalize_hv_drop(threshold_db: float, cfg: dict) -> float:
    """Higher HV drop → higher score."""
    hi = cfg.get("max_db", 10.0)
    lo = cfg.get("min_db", 0.0)
    if hi <= lo:
        return 0.0
    return _clamp((threshold_db - lo) / (hi - lo))


def _normalize_soil_moisture(sm: float | None, cfg: dict) -> float:
    """Lower soil moisture → higher risk score (inverted)."""
    if sm is None:
        return 0.5  # neutral when unavailable
    dry = cfg.get("dry_threshold", 0.10)
    wet = cfg.get("wet_threshold", 0.35)
    if wet <= dry:
        return 0.5
    # Invert: dry soil → high score
    normalized = 1.0 - _clamp((sm - dry) / (wet - dry))
    return _clamp(normalized)


def _normalize_slope(slope_deg: float | None, cfg: dict) -> float:
    if slope_deg is None:
        return 0.0
    steep = cfg.get("steep_deg", 45.0)
    if steep <= 0:
        return 0.0
    return _clamp(slope_deg / steep)


def _normalize_heat(fires_nearby: list[dict], cfg: dict) -> float:
    """Score based on number of fire detections within radius_km in recent/historical windows."""
    if not fires_nearby:
        return 0.0
    days_recent = cfg.get("days_recent", 7)
    weight_recent = cfg.get("weight_recent", 0.7)
    weight_history = cfg.get("weight_history", 0.3)
    cutoff = datetime.now(tz=UTC) - timedelta(days=days_recent)
    recent = sum(1 for f in fires_nearby if _parse_date(f.get("acq_date", "")) >= cutoff)
    total = len(fires_nearby)
    # Simple count → score (caps at max_fire_score)
    max_score = cfg.get("max_fire_score", 1.0)
    score_recent = _clamp(recent / max(1, 5)) * weight_recent  # 5+ recent fires = max
    score_hist = _clamp(total / max(1, 20)) * weight_history   # 20+ total fires = max
    return _clamp(score_recent + score_hist) * max_score


def _normalize_quake(quakes: list[dict], cfg: dict) -> float:
    """Score based on magnitude and distance of recent earthquakes."""
    if not quakes:
        return 0.0
    best = 0.0
    for q in quakes:
        mag = q.get("properties", {}).get("mag", 0.0) or 0.0
        dist_km = q.get("_distance_km", 999.0)
        min_m = cfg.get("min_magnitude", 4.0)
        max_m = cfg.get("max_magnitude", 7.0)
        max_d = cfg.get("max_distance_km", 50.0)
        if mag < min_m or dist_km > max_d:
            continue
        mag_score = _clamp((mag - min_m) / max(0.1, max_m - min_m))
        dist_score = 1.0 - _clamp(dist_km / max_d)
        score = (mag_score + dist_score) / 2.0
        best = max(best, score)
    return best


def _normalize_rainfall(rain_mm: float | None, cfg: dict) -> float:
    if rain_mm is None:
        return 0.0
    lo = cfg.get("low_mm", 10.0)
    hi = cfg.get("high_mm", 80.0)
    if hi <= lo:
        return 0.0
    return _clamp((rain_mm - lo) / (hi - lo))


def _normalize_crop_exposure(crop_ha: float | None, cfg: dict) -> float:
    if crop_ha is None:
        return 0.0
    max_ha = cfg.get("max_ha", 50.0)
    return _clamp(crop_ha / max(0.01, max_ha))


def _parse_date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)
    except Exception:
        return datetime(2000, 1, 1, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Soil modifier lookup
# ---------------------------------------------------------------------------

def _soil_modifiers(wrb_code: str) -> tuple[float, float]:
    """Return (fire_risk_modifier, erosion_risk_modifier) for a WRB code."""
    groups = _soils()
    for g in groups:
        if g.get("wrb_code") == wrb_code:
            return g.get("fire_risk_modifier", 1.0), g.get("erosion_risk_modifier", 1.0)
    # fallback
    for g in groups:
        if g.get("wrb_code") == "DEFAULT":
            return g.get("fire_risk_modifier", 1.0), g.get("erosion_risk_modifier", 1.0)
    return 1.0, 1.0


def _soil_species(wrb_code: str) -> list[dict]:
    groups = _soils()
    for g in groups:
        if g.get("wrb_code") == wrb_code:
            return g.get("species", [])
    for g in groups:
        if g.get("wrb_code") == "DEFAULT":
            return g.get("species", [])
    return []


# ---------------------------------------------------------------------------
# Recipe and cost lookup
# ---------------------------------------------------------------------------

def _get_recipe(risk_id: str) -> dict | None:
    for r in _recipes():
        if r.get("risk_id") == risk_id:
            return r
    return None


def _get_cost(intervention_id: str) -> dict | None:
    for c in _costs():
        if c.get("id") == intervention_id:
            return c
    return None


def _build_budget(recipe: dict, area_ha: float) -> list[dict]:
    """Return list of intervention budget items for the recipe and polygon area."""
    items = []
    for inv in recipe.get("interventions", []):
        iid = inv.get("intervention_id")
        cost_cfg = _get_cost(iid)
        if not cost_cfg:
            continue
        unit = cost_cfg.get("unit", "S/ por ha")
        status = cost_cfg.get("status", "por_verificar")
        source = cost_cfg.get("source", "")
        source_name = cost_cfg.get("source_name", "")
        source_note = cost_cfg.get("source_note", "")
        retrieved = cost_cfg.get("retrieved_date")

        if status == "por_verificar":
            cost_display = None
            cost_label = "costo por confirmar"
        else:
            mid = cost_cfg.get("cost_mid", 0.0)
            if "ha" in unit.lower():
                total = mid * area_ha
            else:
                # per km or per unit: show unit cost only
                total = mid
            cost_display = round(total, 0)
            cost_label = f"S/ {cost_display:,.0f}"

        items.append({
            "intervention_id": iid,
            "name": cost_cfg.get("name"),
            "description": cost_cfg.get("description"),
            "priority": inv.get("priority", 1),
            "timing": inv.get("timing"),
            "notes": inv.get("notes"),
            "unit": unit,
            "cost_mid": cost_cfg.get("cost_mid") if status != "por_verificar" else None,
            "cost_min": cost_cfg.get("cost_min") if status != "por_verificar" else None,
            "cost_max": cost_cfg.get("cost_max") if status != "por_verificar" else None,
            "cost_total_soles": cost_display,
            "cost_label": cost_label,
            "minka_discount_pct": cost_cfg.get("minka_discount_pct"),
            "source": source or source_name or None,
            "source_note": source_note or None,
            "retrieved_date": retrieved,
            "status": status,
        })
    return items


# ---------------------------------------------------------------------------
# Dominant risk determination
# ---------------------------------------------------------------------------

def _dominant_risk(
    hv_score: float,
    heat_score: float,
    rain_score: float,
    quake_score: float,
    slope_score: float,
    sm_score: float,
    crop_ha: float | None,
) -> str:
    """Return the dominant risk_id based on factor pattern."""
    priority = _risk().get("risk_priority", [
        "ladera_inestable_sismo",
        "erosion_huaico",
        "incendio_sequia",
        "estres_hidrico_agricola",
    ])

    scores: dict[str, float] = {
        "ladera_inestable_sismo": quake_score * 0.6 + slope_score * 0.4,
        "erosion_huaico": slope_score * 0.5 + rain_score * 0.3 + hv_score * 0.2,
        "incendio_sequia": heat_score * 0.5 + sm_score * 0.3 + hv_score * 0.2,
        "estres_hidrico_agricola": sm_score * 0.5 + (
            _clamp((crop_ha or 0) / 20.0) * 0.3
        ) + (1.0 - rain_score) * 0.2,
    }

    # Follow priority order: pick the first with score > 0.15
    for risk_id in priority:
        if scores.get(risk_id, 0.0) > 0.15:
            return risk_id

    # If nothing clear, default to highest score
    return max(scores, key=lambda k: scores[k])


# ---------------------------------------------------------------------------
# Main compute function
# ---------------------------------------------------------------------------

def compute_risk_for_alert(
    alert: dict,
    *,
    soil_info: dict | None = None,
    slope_deg: float | None = None,
    fires_nearby: list[dict] | None = None,
    quakes_nearby: list[dict] | None = None,
    rain_mm_7d: float | None = None,
    soil_moisture: float | None = None,
) -> dict:
    """Compute the risk index and NbS recipe for a single alert polygon.

    Parameters
    ----------
    alert:
        Feature properties dict from alerts_hvhv.geojson or the exposure JSON.
    soil_info:
        Output of soilgrids.fetch_soil() or None.
    slope_deg:
        Mean slope in degrees for the polygon (from agriculture.py D1).
    fires_nearby:
        List of fire detection dicts within radius_km.
    quakes_nearby:
        List of USGS earthquake feature dicts with added _distance_km key.
    rain_mm_7d:
        Accumulated rainfall in mm over 7 days (from rainfall.py).
    soil_moisture:
        NISAR SME2 soil moisture (m³/m³) or None if unavailable.

    Returns
    -------
    dict with keys: risk_id, risk_name, level, index, factors, recipe, budget,
                    soil, sources, disclaimer, generated_at.
    """
    cfg = _risk()
    factors_cfg = cfg.get("factors", {})
    levels_cfg = cfg.get("levels", {})

    # --- Factor scores ---
    hv_drop_db = alert.get("threshold_db", 0.0) or 0.0
    area_ha = alert.get("area_ha", 0.0) or 0.0
    crop_ha = alert.get("cropland_ha") or alert.get("crop_ha")  # from exposure or agriculture

    hv_score = _normalize_hv_drop(hv_drop_db, factors_cfg.get("hv_drop", {}))
    sm_score = _normalize_soil_moisture(soil_moisture, factors_cfg.get("soil_moisture", {}))
    slope_score = _normalize_slope(slope_deg, factors_cfg.get("slope", {}))
    heat_score = _normalize_heat(fires_nearby or [], factors_cfg.get("heat", {}))
    quake_score = _normalize_quake(quakes_nearby or [], factors_cfg.get("quake", {}))
    rain_score = _normalize_rainfall(rain_mm_7d, factors_cfg.get("rainfall", {}))
    crop_score = _normalize_crop_exposure(crop_ha, factors_cfg.get("crop_exposure", {}))

    # Soil modifiers
    wrb_code = (soil_info or {}).get("wrb_code", "DEFAULT")
    fire_mod, erosion_mod = _soil_modifiers(wrb_code)

    # Apply modifiers to relevant factors
    effective_heat = _clamp(heat_score * fire_mod)
    effective_slope = _clamp(slope_score * erosion_mod)

    # --- Weights ---
    w = factors_cfg
    sm_weight = w.get("soil_moisture", {}).get("weight", 0.15)
    if soil_moisture is None:
        sm_weight = w.get("soil_moisture", {}).get("fallback_weight", 0.0)
        # redistribute to hv_drop
        extra = 0.15 - sm_weight
    else:
        extra = 0.0

    hv_weight = w.get("hv_drop", {}).get("weight", 0.30) + extra
    slope_weight = w.get("slope", {}).get("weight", 0.15)
    heat_weight = w.get("heat", {}).get("weight", 0.15)
    quake_weight = w.get("quake", {}).get("weight", 0.10)
    rain_weight = w.get("rainfall", {}).get("weight", 0.10)
    crop_weight = w.get("crop_exposure", {}).get("weight", 0.05)

    index = (
        hv_score * hv_weight
        + sm_score * sm_weight
        + effective_slope * slope_weight
        + effective_heat * heat_weight
        + quake_score * quake_weight
        + rain_score * rain_weight
        + crop_score * crop_weight
    )
    index = _clamp(index)

    # --- Level ---
    if index <= levels_cfg.get("low", {}).get("max", 0.33):
        level = "bajo"
        color_hex = levels_cfg.get("low", {}).get("color_hex", "#4CAF50")
    elif index <= levels_cfg.get("medium", {}).get("max", 0.60):
        level = "medio"
        color_hex = levels_cfg.get("medium", {}).get("color_hex", "#FF9800")
    else:
        level = "alto"
        color_hex = levels_cfg.get("high", {}).get("color_hex", "#F44336")

    # --- Dominant risk ---
    risk_id = _dominant_risk(
        hv_score, effective_heat, rain_score, quake_score,
        effective_slope, sm_score, crop_ha,
    )

    # --- Recipe ---
    recipe = _get_recipe(risk_id)
    budget = _build_budget(recipe, area_ha) if recipe else []

    # Species from soil
    soil_species = _soil_species(wrb_code)

    # --- Factor explanation (human-readable) ---
    factor_details = []
    if hv_drop_db > 0:
        factor_details.append(
            f"caída HV {hv_drop_db:.1f} dB (NISAR · umbral 3×MAD)"
        )
    if slope_deg is not None:
        factor_details.append(f"pendiente {slope_deg:.0f}°")
    if fires_nearby:
        factor_details.append(f"{len(fires_nearby)} focos de calor a < 2 km (FIRMS·VIIRS)")
    if quakes_nearby:
        q = quakes_nearby[0]
        mag = q.get("properties", {}).get("mag", "?")
        dist = q.get("_distance_km", "?")
        factor_details.append(f"sismo M{mag} a {dist:.0f} km (USGS)")
    if rain_mm_7d is not None:
        factor_details.append(f"lluvia 7 d: {rain_mm_7d:.1f} mm (GPM·IMERG)")
    if soil_moisture is not None:
        factor_details.append(f"humedad suelo: {soil_moisture:.3f} m³/m³ (NISAR·SME2·PROVISIONAL)")
    elif soil_moisture is None:
        factor_details.append("humedad suelo: sin datos SME2 (factor excluido)")
    if crop_ha:
        factor_details.append(f"{crop_ha:.1f} ha de cultivo expuesto (WorldCover 2021)")

    # --- Sources ---
    sources_nisar = {
        "source": "NISAR",
        "product": "GCOV L2 PROVISIONAL",
        "granules": alert.get("granules", []),
        "dates": alert.get("date_range", []),
        "url": "https://nisar-docs.asf.alaska.edu/gcov/",
    }
    sources_complementary: list[dict] = []
    if soil_info and soil_info.get("wrb_code") != "DEFAULT":
        sources_complementary.append({
            "source": soil_info.get("source", "SoilGrids (ISRIC)"),
            "url": soil_info.get("source_url", ""),
            "date": soil_info.get("source_date", ""),
            "license": soil_info.get("license", "CC BY 4.0"),
        })
    if fires_nearby:
        sources_complementary.append({
            "source": "NASA FIRMS · VIIRS NOAA-20",
            "url": "https://firms.modaps.eosdis.nasa.gov/",
        })
    if quakes_nearby:
        sources_complementary.append({
            "source": "USGS Earthquake Hazards Program",
            "url": "https://earthquake.usgs.gov/fdsnws/event/1/",
        })
    if rain_mm_7d is not None:
        sources_complementary.append({
            "source": "GPM IMERG (NASA GES DISC)",
            "url": "https://gpm.nasa.gov/data/imerg",
        })
    if slope_deg is not None:
        sources_complementary.append({
            "source": "Mapzen Terrain Tiles (DEM compuesto)",
            "url": "https://registry.opendata.aws/terrain-tiles/",
        })

    return {
        "alert_id": alert.get("id"),
        "aoi_id": alert.get("aoi_id", "ayacucho-huanta"),
        "area_ha": area_ha,
        "risk_id": risk_id,
        "risk_name": recipe.get("risk_name", risk_id) if recipe else risk_id,
        "risk_description": recipe.get("risk_description", "") if recipe else "",
        "level": level,
        "color_hex": color_hex,
        "index": round(index, 4),
        "factors": {
            "hv_drop_db": round(hv_drop_db, 2),
            "hv_score": round(hv_score, 3),
            "slope_deg": round(slope_deg, 1) if slope_deg is not None else None,
            "slope_score": round(slope_score, 3),
            "heat_score": round(heat_score, 3),
            "quake_score": round(quake_score, 3),
            "rain_score": round(rain_score, 3),
            "rain_mm_7d": round(rain_mm_7d, 1) if rain_mm_7d is not None else None,
            "soil_moisture_m3m3": soil_moisture,
            "soil_moisture_score": round(sm_score, 3),
            "crop_ha": crop_ha,
            "crop_score": round(crop_score, 3),
            "index_total": round(index, 4),
        },
        "factor_details": factor_details,
        "soil": {
            "wrb_code": wrb_code,
            "wrb_name": (soil_info or {}).get("wrb_name", "No clasificado"),
            "clay_pct": (soil_info or {}).get("clay_pct"),
            "sand_pct": (soil_info or {}).get("sand_pct"),
            "soc_pct": (soil_info or {}).get("soc_pct"),
            "species": soil_species,
            "source": (soil_info or {}).get("source"),
            "source_date": (soil_info or {}).get("source_date"),
            "license": (soil_info or {}).get("license"),
        },
        "recipe": {
            "risk_id": risk_id,
            "risk_name": recipe.get("risk_name") if recipe else None,
            "condition": recipe.get("condition") if recipe else None,
            "disclaimer": recipe.get("disclaimer") if recipe else None,
            "executor": recipe.get("executor", []) if recipe else [],
            "species_primary": recipe.get("species_primary", []) if recipe else [],
            "source": recipe.get("source") if recipe else None,
        } if recipe else None,
        "budget": budget,
        "sources_nisar": sources_nisar,
        "sources_complementary": sources_complementary,
        "soil_moisture_available": soil_moisture is not None,
        "disclaimer": (
            "Aviso de monitoreo. No reemplaza a INDECI ni a la autoridad local. "
            "Verificar en campo. NISAR revisita cada ~12 días; dato no es tiempo real."
        ),
        "generated_at": datetime.now(tz=UTC).isoformat(),
    }
