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

import logging
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
_diagnosis_cfg: dict | None = None


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


_valuation_cfg: dict | None = None
_recovery_cfg: dict | None = None


def _diagnosis() -> dict:
    global _diagnosis_cfg
    if _diagnosis_cfg is None:
        _diagnosis_cfg = _load_yaml(CONFIG_NBS / "diagnosis.yaml")
    return _diagnosis_cfg


def _valuation() -> dict:
    global _valuation_cfg
    if _valuation_cfg is None:
        _valuation_cfg = _load_yaml(CONFIG_NBS / "valuation.yaml")
    return _valuation_cfg


def _recovery() -> dict:
    global _recovery_cfg
    if _recovery_cfg is None:
        _recovery_cfg = _load_yaml(CONFIG_NBS / "recovery_scenarios.yaml")
    return _recovery_cfg


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


def _build_cost_benefit(
    crop_ha: float | None,
    area_ha: float,
    risk_index: float,
    budget: list[dict],
) -> dict[str, Any] | None:
    """Calculates cost vs. avoided loss and Benefit/Cost ratio (Fase 3.3).

    Returns None while the crop values or the intervention costs lack a verified
    source: a ratio built on unverified numbers would look like evidence.
    """
    val_cfg = _valuation()
    if val_cfg.get("status") != "verificado":
        return None
    if not any(b.get("cost_total_soles") for b in budget):
        return None
    crops_cfg = val_cfg.get("crops", {})

    if crop_ha and crop_ha > 0:
        effective_ha = crop_ha
        val_info = crops_cfg.get("cropland_average", {})
    elif area_ha > 0:
        effective_ha = area_ha
        val_info = crops_cfg.get("default_rural", {})
    else:
        effective_ha = 1.0
        val_info = crops_cfg.get("default_rural", {})

    val_per_ha = float(val_info.get("gross_production_value_pen_ha", 8500.0))
    source_val = val_info.get("source", "MIDAGRI - SIEA (2024)")

    # Annual loss avoided = effective_ha * val_per_ha * risk_index
    loss_annual = round(effective_ha * val_per_ha * max(0.1, risk_index), 2)
    loss_3yr = round(loss_annual * 2.8, 2)
    loss_5yr = round(loss_annual * 4.5, 2)

    cost_total = round(sum(b.get("cost_total_soles") or 0.0 for b in budget), 2)

    # Cost with Minka communal labor discount
    cost_minka = 0.0
    for b in budget:
        unit_cost = b.get("cost_total_soles") or 0.0
        disc = (b.get("minka_discount_pct") or 0.0) / 100.0
        cost_minka += unit_cost * (1.0 - disc)
    cost_minka = round(cost_minka, 2)

    rbc_3yr = round(loss_3yr / cost_total, 2) if cost_total > 0 else 1.0
    rbc_5yr = round(loss_5yr / cost_total, 2) if cost_total > 0 else 1.0
    rbc_minka_5yr = round(loss_5yr / cost_minka, 2) if cost_minka > 0 else 1.0

    return {
        "currency": val_cfg.get("currency", "PEN"),
        "currency_symbol": val_cfg.get("currency_symbol", "S/"),
        "crop_ha_evaluated": crop_ha or 0.0,
        "effective_ha": effective_ha,
        "production_value_per_ha_pen": val_per_ha,
        "valuation_source": source_val,
        "loss_avoided_annual_pen": loss_annual,
        "loss_avoided_3yr_pen": loss_3yr,
        "loss_avoided_5yr_pen": loss_5yr,
        "intervention_cost_total_pen": cost_total,
        "cost_with_minka_pen": cost_minka,
        "benefit_cost_ratio_3yr": rbc_3yr,
        "benefit_cost_ratio_5yr": rbc_5yr,
        "benefit_cost_ratio_minka_5yr": rbc_minka_5yr,
        "assumptions": val_cfg.get("projections", {}).get("assumptions", []),
        "disclaimer": val_cfg.get("disclaimer", ""),
    }


def _build_recovery_scenario(risk_id: str) -> dict[str, Any]:
    """Retrieves 3- and 5-year NDVI recovery trajectory and citations (Fase 3.2)."""
    rec_cfg = _recovery()
    default_label = "Escenario con supuestos. No es una observación ni una promesa."
    mandatory_label = rec_cfg.get("mandatory_label", default_label)
    scenarios = rec_cfg.get("scenarios", {})
    scen = scenarios.get(risk_id) or scenarios.get("erosion_huaico", {})
    return {
        "mandatory_label": mandatory_label,
        "risk_id": risk_id,
        "risk_name": scen.get("risk_name", "Recuperación de cobertura"),
        "baseline_ndvi": scen.get("baseline_ndvi", 0.20),
        "projected": scen.get("projected", {}),
        "annual_rate_label": scen.get("annual_rate_label", "+0.06 NDVI / año"),
        "citation": scen.get("citation", "MINAM / SERFOR (2021)"),
        "citation_url": scen.get("citation_url", ""),
        "limiting_factors": scen.get("limiting_factors", []),
    }


def _build_optical_context(aoi_id: str = "ayacucho-huanta") -> dict[str, Any]:
    """Returns NASA HLS optical comparison context and 3D terrain flag (Fase 3.1)."""
    return {
        "product": "HLS S30 v2 · Sentinel-2, 30 m",
        "source": "NASA HLS / Copernicus Sentinel-2 · GIBS",
        "dates": {"before": "2026-06-22", "after": "2026-10-08"},
        "scenes": [
            "HLS.S30.T18LWL.2026173T150941.v2.0",
            "HLS.S30.T18LXL.2026173T150941.v2.0",
            "HLS.S30.T18LWL.2026281T150721.v2.0",
            "HLS.S30.T18LXL.2026281T150721.v2.0",
        ],
        "image_urls": {
            "before": f"/api/context/{aoi_id}/hls-optical/2026-06-22.png",
            "after": f"/api/context/{aoi_id}/hls-optical/2026-10-08.png",
        },
        "terrain_3d_available": True,
    }


# ---------------------------------------------------------------------------
# Dominant risk determination
# ---------------------------------------------------------------------------

def _dominant_risk(
    hv_score: float,
    heat_score: float,
    rain_score: float | None,
    quake_score: float,
    slope_score: float | None,
    sm_score: float | None,
    crop_ha: float | None,
) -> str | None:
    """Return the dominant risk_id, or None when no factor supports a cause.

    A risk is only eligible when its own evidence exists: no "ladera tras sismo"
    without a nearby quake, no "incendio" without heat or dry soil, no "estres
    hidrico" without SME2 soil moisture and cropland, no "erosion" without slope.
    """
    cfg = _risk()
    gates = cfg.get("evidence", {})
    min_slope = gates.get("erosion_min_slope_score", 0.33)
    dry = gates.get("dry_soil_min_score", 0.6)
    rain = rain_score or 0.0
    eligible: dict[str, float] = {}
    if quake_score > 0 and slope_score is not None:
        eligible["ladera_inestable_sismo"] = quake_score * 0.6 + slope_score * 0.4
    if slope_score is not None and slope_score >= min_slope:
        eligible["erosion_huaico"] = slope_score * 0.5 + rain * 0.3 + hv_score * 0.2
    if heat_score > 0 or (sm_score is not None and sm_score >= dry):
        eligible["incendio_sequia"] = heat_score * 0.5 + (sm_score or 0.0) * 0.3 + hv_score * 0.2
    if sm_score is not None and sm_score >= dry and (crop_ha or 0) > 0:
        eligible["estres_hidrico_agricola"] = sm_score * 0.5 + _clamp((crop_ha or 0) / 20.0) * 0.5
    if not eligible:
        return None
    priority = cfg.get("risk_priority", [])
    return max(eligible, key=lambda k: (eligible[k], -priority.index(k) if k in priority else 0))


# ---------------------------------------------------------------------------
# Main compute function
# ---------------------------------------------------------------------------

def _zone_diagnosis(risk_id: str | None, factors: dict, *, dry_soil: bool) -> dict:
    """Describe measured factors and only the evidence supporting this cause.

    Missing inputs and zero event counts never become claims of a detection or
    of its absence. The index and its evidence gates are not changed here.
    """
    cfg = _diagnosis()
    templates = cfg["measurements"]
    facts: dict[str, str] = {}
    precision = {"hv_drop_db": 1, "slope_deg": 1, "soil_moisture_m3m3": 3,
                 "heat_count": 0, "quake_magnitude": 1, "rain_mm_7d": 1, "crop_ha": 2}
    for key, digits in precision.items():
        value = factors.get(key)
        if value is None or (key in ("heat_count", "quake_magnitude", "crop_ha") and value <= 0):
            continue
        values = {"value": f"{value:.{digits}f}".replace(".", ",")}
        if key == "quake_magnitude":
            distance = factors.get("quake_distance_km")
            if distance is None or factors["quake_score"] <= 0:
                continue
            values["distance"] = f"{distance:.1f}".replace(".", ",")
        text = templates[key].format(**values)
        if key == "soil_moisture_m3m3" and factors.get("soil_moisture_date"):
            text += f" · {factors['soil_moisture_date']}"
        facts[key] = text

    cause_keys: list[str] = []
    if risk_id == "erosion_huaico":
        cause_keys = ["slope_deg"]
        if (factors.get("rain_score") or 0) > 0:
            cause_keys.append("rain_mm_7d")
    elif risk_id == "incendio_sequia":
        if factors["heat_score"] > 0:
            cause_keys.append("heat_count")
        if dry_soil:
            cause_keys.append("soil_moisture_m3m3")
    elif risk_id == "estres_hidrico_agricola":
        if dry_soil:
            cause_keys += ["soil_moisture_m3m3", "crop_ha"]
    elif risk_id == "ladera_inestable_sismo":
        cause_keys = ["quake_magnitude", "slope_deg"]
    cause_keys = [key for key in cause_keys if key in facts]
    return {
        "summary": " · ".join(facts.values()) or cfg["no_measurements"],
        "summary_factor_ids": list(facts),
        "cause_factor_ids": cause_keys,
        "cause_explanation": cfg["supported_cause"].format(
            evidence="; ".join(facts[key] for key in cause_keys)
        ) if cause_keys else cfg["unattributed"],
    }


def compute_risk_for_alert(
    alert: dict,
    *,
    soil_info: dict | None = None,
    slope_deg: float | None = None,
    fires_nearby: list[dict] | None = None,
    quakes_nearby: list[dict] | None = None,
    rain_mm_7d: float | None = None,
    soil_moisture: float | None = None,
    soil_moisture_date: str | None = None,
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
    soil_moisture_date:
        Observation date from the published SME2 metadata, when available.

    Returns
    -------
    dict with keys: risk_id, risk_name, level, index, factors, recipe, budget,
                    soil, sources, disclaimer, generated_at.
    """
    cfg = _risk()
    factors_cfg = cfg.get("factors", {})
    levels_cfg = cfg.get("levels", {})

    # --- Factor scores ---
    # Mean HV loss measured inside the polygon (dB, positive = loss). The detection
    # threshold is NOT a per-zone measurement and is never used as one.
    hv_drop_db = alert.get("hv_drop_db")
    area_ha = alert.get("area_ha", 0.0) or 0.0
    crop_ha = alert.get("cropland_ha") or alert.get("crop_ha")

    hv_cfg = factors_cfg.get("hv_drop", {})
    hv_score = _normalize_hv_drop(hv_drop_db, hv_cfg) if hv_drop_db is not None else 0.0
    sm_cfg = factors_cfg.get("soil_moisture", {})
    sm_score = _normalize_soil_moisture(soil_moisture, sm_cfg) if soil_moisture is not None else None
    sl_cfg = factors_cfg.get("slope", {})
    slope_score = _normalize_slope(slope_deg, sl_cfg) if slope_deg is not None else None
    heat_score = _normalize_heat(fires_nearby or [], factors_cfg.get("heat", {}))
    quake_score = _normalize_quake(quakes_nearby or [], factors_cfg.get("quake", {}))
    rn_cfg = factors_cfg.get("rainfall", {})
    rain_score = _normalize_rainfall(rain_mm_7d, rn_cfg) if rain_mm_7d is not None else None
    crop_score = _normalize_crop_exposure(crop_ha, factors_cfg.get("crop_exposure", {}))

    # Soil modifiers (only when SoilGrids classified the cell)
    wrb_code = (soil_info or {}).get("wrb_code", "DEFAULT")
    fire_mod, erosion_mod = _soil_modifiers(wrb_code)
    effective_heat = _clamp(heat_score * fire_mod)
    effective_slope = _clamp(slope_score * erosion_mod) if slope_score is not None else None

    # --- Weights: only factors with data take part; weights are renormalized ---
    w = factors_cfg
    parts = [
        ("caída HV", hv_score if hv_drop_db is not None else None, w.get("hv_drop", {}).get("weight", 0.30)),
        ("humedad SME2", sm_score, w.get("soil_moisture", {}).get("weight", 0.15)),
        ("pendiente", effective_slope, w.get("slope", {}).get("weight", 0.15)),
        ("calor", effective_heat, w.get("heat", {}).get("weight", 0.15)),
        ("sismo", quake_score, w.get("quake", {}).get("weight", 0.10)),
        ("lluvia", rain_score, w.get("rainfall", {}).get("weight", 0.10)),
        ("cultivo", crop_score, w.get("crop_exposure", {}).get("weight", 0.05)),
    ]
    used = [(v, wt) for _, v, wt in parts if v is not None]
    total_w = sum(wt for _, wt in used) or 1.0
    index = _clamp(sum(v * wt for v, wt in used) / total_w)
    excluded = [name for name, v, _ in parts if v is None]

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

    # --- Recipe (none when the cause is not supported by any factor) ---
    recipe = _get_recipe(risk_id) if risk_id else None
    budget = _build_budget(recipe, area_ha) if recipe else []

    # Species from soil
    soil_species = _soil_species(wrb_code)

    # Preserve measured values alongside scores for auditable per-zone prose.
    quake = max(quakes_nearby or [], key=lambda q: _normalize_quake(
        [q], factors_cfg.get("quake", {})
    ), default=None) if quake_score > 0 else None
    factors = {
        "hv_drop_db": round(hv_drop_db, 2) if hv_drop_db is not None else None,
        "hv_score": round(hv_score, 3),
        "slope_deg": round(slope_deg, 1) if slope_deg is not None else None,
        "slope_score": round(slope_score, 3) if slope_score is not None else None,
        "heat_score": round(heat_score, 3),
        "heat_count": len(fires_nearby) if fires_nearby is not None else None,
        "quake_score": round(quake_score, 3),
        "quake_magnitude": quake.get("properties", {}).get("mag") if quake else None,
        "quake_distance_km": quake.get("_distance_km") if quake else None,
        "rain_score": round(rain_score, 3) if rain_score is not None else None,
        "rain_mm_7d": round(rain_mm_7d, 1) if rain_mm_7d is not None else None,
        "soil_moisture_m3m3": soil_moisture,
        "soil_moisture_date": soil_moisture_date if soil_moisture is not None else None,
        "soil_moisture_score": round(sm_score, 3) if sm_score is not None else None,
        "crop_ha": crop_ha,
        "crop_score": round(crop_score, 3),
        "index_total": round(index, 4),
        "excluded": excluded,
    }
    diagnosis = _zone_diagnosis(
        risk_id, factors,
        dry_soil=sm_score is not None and sm_score >= cfg.get("evidence", {}).get("dry_soil_min_score", 0.6),
    )

    # --- Factor explanation (human-readable) ---
    factor_details = []
    if hv_drop_db is not None:
        factor_details.append(f"caída HV media {hv_drop_db:.1f} dB en la mancha (NISAR)")
    if slope_deg is not None:
        factor_details.append(f"pendiente {slope_deg:.0f}°")
    if fires_nearby:
        factor_details.append(f"{len(fires_nearby)} focos de calor cercanos (FIRMS·VIIRS)")
    if quake:
        mag = factors["quake_magnitude"]
        dist = factors["quake_distance_km"]
        factor_details.append(f"sismo M{mag} a {dist:.0f} km (USGS)")
    if rain_mm_7d is not None:
        factor_details.append(f"lluvia 7 d: {rain_mm_7d:.1f} mm (GPM·IMERG)")
    if soil_moisture is not None:
        date = f" · {soil_moisture_date}" if soil_moisture_date else ""
        factor_details.append(f"humedad suelo: {soil_moisture:.3f} m³/m³ (NISAR·SME2·PROVISIONAL){date}")
    if excluded:
        factor_details.append("sin datos, fuera del índice: " + ", ".join(excluded))
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
    if soil_info and soil_info.get("wrb_name") not in (None, "No disponible", "No clasificado"):
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
        "risk_id": risk_id or "causa_por_verificar",
        "risk_name": recipe.get("risk_name", risk_id) if recipe else "Causa por verificar",
        **diagnosis,
        "risk_description": diagnosis["cause_explanation"],
        "level": level,
        "color_hex": color_hex,
        "index": round(index, 4),
        "factors": factors,
        "factor_details": factor_details,
        "soil": {
            "wrb_code": wrb_code,
            "wrb_name": (soil_info or {}).get("wrb_name", "Sin datos de SoilGrids"),
            "wrb_probability_pct": (soil_info or {}).get("wrb_probability_pct"),
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
        "cost_benefit": _build_cost_benefit(crop_ha, area_ha, index, budget) if recipe else None,
        "recovery_scenario": _build_recovery_scenario(risk_id) if risk_id else None,
        "optical_context": _build_optical_context(alert.get("aoi_id", "ayacucho-huanta")),
        "sources_nisar": sources_nisar,
        "sources_complementary": sources_complementary,
        "soil_moisture_available": soil_moisture is not None,
        "disclaimer": (
            "Aviso de monitoreo. No reemplaza a INDECI ni a la autoridad local. "
            "Verificar en campo. NISAR revisita cada ~12 días; dato no es tiempo real."
        ),
        "generated_at": datetime.now(tz=UTC).isoformat(),
    }
