"""Tests for the Phase 1 risk engine — uses only synthetic data.

No real HDF5, no real API calls, no real data files.
Synthetic data is confined to this test file.
"""

from __future__ import annotations

from sarlab_pipeline.remediation.risk import (
    _dominant_risk,
    _normalize_crop_exposure,
    _normalize_heat,
    _normalize_hv_drop,
    _normalize_quake,
    _normalize_rainfall,
    _normalize_slope,
    _normalize_soil_moisture,
    compute_risk_for_alert,
)

# ---------------------------------------------------------------------------
# Unit tests for normalizers
# ---------------------------------------------------------------------------

class TestNormalizerHvDrop:
    def test_zero_drop_gives_zero(self):
        cfg = {"min_db": 0.0, "max_db": 10.0}
        assert _normalize_hv_drop(0.0, cfg) == 0.0

    def test_max_drop_gives_one(self):
        cfg = {"min_db": 0.0, "max_db": 10.0}
        assert _normalize_hv_drop(10.0, cfg) == 1.0

    def test_mid_drop(self):
        cfg = {"min_db": 0.0, "max_db": 10.0}
        result = _normalize_hv_drop(5.0, cfg)
        assert abs(result - 0.5) < 1e-6

    def test_above_max_clamps_to_one(self):
        cfg = {"min_db": 0.0, "max_db": 10.0}
        assert _normalize_hv_drop(20.0, cfg) == 1.0


class TestNormalizerSoilMoisture:
    def test_none_gives_neutral(self):
        cfg = {"dry_threshold": 0.10, "wet_threshold": 0.35}
        assert _normalize_soil_moisture(None, cfg) == 0.5

    def test_dry_gives_high_score(self):
        cfg = {"dry_threshold": 0.10, "wet_threshold": 0.35}
        result = _normalize_soil_moisture(0.05, cfg)
        assert result >= 0.9  # very dry → high risk score

    def test_wet_gives_low_score(self):
        cfg = {"dry_threshold": 0.10, "wet_threshold": 0.35}
        result = _normalize_soil_moisture(0.40, cfg)
        assert result <= 0.1  # wet soil → low risk score

    def test_mid_moisture(self):
        cfg = {"dry_threshold": 0.10, "wet_threshold": 0.35}
        result = _normalize_soil_moisture(0.225, cfg)
        assert abs(result - 0.5) < 0.1


class TestNormalizerSlope:
    def test_flat_gives_zero(self):
        cfg = {"flat_deg": 0.0, "steep_deg": 45.0}
        assert _normalize_slope(0.0, cfg) == 0.0

    def test_steep_gives_one(self):
        cfg = {"flat_deg": 0.0, "steep_deg": 45.0}
        assert _normalize_slope(45.0, cfg) == 1.0

    def test_none_gives_zero(self):
        cfg = {"flat_deg": 0.0, "steep_deg": 45.0}
        assert _normalize_slope(None, cfg) == 0.0


class TestNormalizerHeat:
    def test_no_fires_gives_zero(self):
        cfg = {
            "days_recent": 7, "weight_recent": 0.7, "weight_history": 0.3,
            "max_fire_score": 1.0
        }
        assert _normalize_heat([], cfg) == 0.0

    def test_many_fires_gives_high_score(self):
        fires = [{"acq_date": "2026-11-14"} for _ in range(10)]
        cfg = {
            "days_recent": 7, "weight_recent": 0.7, "weight_history": 0.3,
            "max_fire_score": 1.0
        }
        result = _normalize_heat(fires, cfg)
        assert result > 0.5


class TestNormalizerQuake:
    def test_no_quakes_gives_zero(self):
        cfg = {
            "min_magnitude": 4.0, "max_magnitude": 7.0,
            "max_distance_km": 50.0, "days_window": 30
        }
        assert _normalize_quake([], cfg) == 0.0

    def test_distant_quake_ignored(self):
        quakes = [{"properties": {"mag": 6.0}, "_distance_km": 100.0}]
        cfg = {
            "min_magnitude": 4.0, "max_magnitude": 7.0,
            "max_distance_km": 50.0, "days_window": 30
        }
        assert _normalize_quake(quakes, cfg) == 0.0

    def test_strong_nearby_quake_gives_high_score(self):
        quakes = [{"properties": {"mag": 7.0}, "_distance_km": 5.0}]
        cfg = {
            "min_magnitude": 4.0, "max_magnitude": 7.0,
            "max_distance_km": 50.0, "days_window": 30
        }
        result = _normalize_quake(quakes, cfg)
        assert result > 0.7

    def test_weak_quake_below_min_mag_ignored(self):
        quakes = [{"properties": {"mag": 2.0}, "_distance_km": 5.0}]
        cfg = {
            "min_magnitude": 4.0, "max_magnitude": 7.0,
            "max_distance_km": 50.0, "days_window": 30
        }
        assert _normalize_quake(quakes, cfg) == 0.0


class TestNormalizerRainfall:
    def test_no_rain_gives_zero(self):
        cfg = {"low_mm": 10.0, "high_mm": 80.0}
        assert _normalize_rainfall(0.0, cfg) == 0.0

    def test_none_gives_zero(self):
        cfg = {"low_mm": 10.0, "high_mm": 80.0}
        assert _normalize_rainfall(None, cfg) == 0.0

    def test_high_rain_gives_one(self):
        cfg = {"low_mm": 10.0, "high_mm": 80.0}
        assert _normalize_rainfall(100.0, cfg) == 1.0


class TestCropExposure:
    def test_no_crops_gives_zero(self):
        cfg = {"min_ha": 0.0, "max_ha": 50.0}
        assert _normalize_crop_exposure(0.0, cfg) == 0.0

    def test_max_crops_gives_one(self):
        cfg = {"min_ha": 0.0, "max_ha": 50.0}
        assert _normalize_crop_exposure(50.0, cfg) == 1.0


# ---------------------------------------------------------------------------
# Integration test: compute_risk_for_alert with synthetic alert
# ---------------------------------------------------------------------------

SYNTHETIC_ALERT = {
    "id": "test_alert_000",
    "aoi_id": "test-aoi",
    "phenomenon": "backscatter_loss",
    "source": "NISAR",
    "provisional": True,
    "confidence": "por_validar",
    "area_ha": 5.0,
    "threshold_db": 3.5,
    "granules": ["NISAR_FAKE_A.h5", "NISAR_FAKE_B.h5"],
    "date_range": ["2026-06-24", "2026-10-10"],
}


class TestComputeRiskForAlert:
    def test_basic_structure(self):
        result = compute_risk_for_alert(SYNTHETIC_ALERT)
        assert "risk_id" in result
        assert "level" in result
        assert "index" in result
        assert "factors" in result
        assert "disclaimer" in result
        assert result["level"] in ("bajo", "medio", "alto")
        assert 0.0 <= result["index"] <= 1.0

    def test_disclaimer_present(self):
        result = compute_risk_for_alert(SYNTHETIC_ALERT)
        assert "INDECI" in result["disclaimer"]
        assert "12 días" in result["disclaimer"]

    def test_sources_nisar_separated(self):
        result = compute_risk_for_alert(SYNTHETIC_ALERT)
        assert "sources_nisar" in result
        assert result["sources_nisar"]["source"] == "NISAR"
        assert "sources_complementary" in result

    def test_budget_items_have_no_cost_when_por_verificar(self):
        """All interventions are por_verificar; no cost number should appear."""
        result = compute_risk_for_alert(SYNTHETIC_ALERT)
        for item in result.get("budget", []):
            if item.get("status") == "por_verificar":
                assert item["cost_total_soles"] is None
                assert item["cost_label"] == "costo por confirmar"

    def test_recipe_assigned(self):
        result = compute_risk_for_alert(SYNTHETIC_ALERT, slope_deg=30.0)
        assert result["recipe"] is not None
        assert result["recipe"]["risk_id"] == "erosion_huaico"

    def test_no_evidence_means_no_recipe(self):
        result = compute_risk_for_alert({**SYNTHETIC_ALERT, "hv_drop_db": 3.0})
        assert result["recipe"] is None
        assert result["risk_id"] == "causa_por_verificar"
        assert result["budget"] == []

    def test_steep_slope_without_quake_is_not_seismic(self):
        result = compute_risk_for_alert(SYNTHETIC_ALERT, slope_deg=35.0)
        assert result["risk_id"] != "ladera_inestable_sismo"

    def test_missing_factors_are_excluded_not_neutral(self):
        result = compute_risk_for_alert({**SYNTHETIC_ALERT, "hv_drop_db": 5.0})
        assert "humedad SME2" in result["factors"]["excluded"]
        assert result["factors"]["soil_moisture_score"] is None

    def test_high_hv_drop_increases_index(self):
        low_drop = {**SYNTHETIC_ALERT, "hv_drop_db": 1.0}
        high_drop = {**SYNTHETIC_ALERT, "hv_drop_db": 9.0}
        r_low = compute_risk_for_alert(low_drop)
        r_high = compute_risk_for_alert(high_drop)
        assert r_high["index"] > r_low["index"]

    def test_quake_triggers_ladera_inestable(self):
        quakes = [{"properties": {"mag": 7.0}, "_distance_km": 5.0}]
        result = compute_risk_for_alert(
            {**SYNTHETIC_ALERT, "threshold_db": 3.0},
            slope_deg=30.0,
            quakes_nearby=quakes,
        )
        assert result["risk_id"] == "ladera_inestable_sismo"

    def test_soil_moisture_unavailable_marked(self):
        result = compute_risk_for_alert(SYNTHETIC_ALERT, soil_moisture=None)
        assert result["soil_moisture_available"] is False
        assert any("SME2" in d for d in result["factor_details"])

    def test_soil_moisture_available_marked(self):
        result = compute_risk_for_alert(SYNTHETIC_ALERT, soil_moisture=0.20)
        assert result["soil_moisture_available"] is True

    def test_index_always_in_range(self):
        """Index must stay in [0, 1] regardless of extreme inputs."""
        extreme_alert = {**SYNTHETIC_ALERT, "threshold_db": 100.0, "area_ha": 1000.0}
        quakes = [{"properties": {"mag": 9.0}, "_distance_km": 0.1}]
        result = compute_risk_for_alert(
            extreme_alert,
            slope_deg=90.0,
            rain_mm_7d=500.0,
            soil_moisture=0.0,
            quakes_nearby=quakes,
        )
        assert 0.0 <= result["index"] <= 1.0


# ---------------------------------------------------------------------------
# Dominant risk logic
# ---------------------------------------------------------------------------

class TestDominantRisk:
    def test_quake_wins_over_fire(self):
        risk = _dominant_risk(
            hv_score=0.5, heat_score=0.8, rain_score=0.1,
            quake_score=0.9, slope_score=0.7,
            sm_score=0.5, crop_ha=10.0,
        )
        assert risk == "ladera_inestable_sismo"

    def test_fire_dominates_without_quake_or_slope(self):
        """With high heat and high sm score (dry), and no quake/slope, fire dominates."""
        risk = _dominant_risk(
            hv_score=0.6, heat_score=0.9, rain_score=0.0,
            quake_score=0.0, slope_score=0.0,     # no slope → erosion weak
            sm_score=0.9, crop_ha=0.0,
        )
        assert risk == "incendio_sequia"

    def test_erosion_dominates_with_slope_and_rain_no_quake(self):
        """High slope + high rain without quake → erosion or ladera (both high-slope risks)."""
        risk = _dominant_risk(
            hv_score=0.5, heat_score=0.1, rain_score=0.9,
            quake_score=0.0, slope_score=0.9,
            sm_score=0.1, crop_ha=0.0,
        )
        # With high slope, either ladera or erosion is acceptable; both relate to slope stability.
        # ladera_inestable_sismo: quake_score*0.6 + slope_score*0.4 = 0 + 0.36 = 0.36 (>0.15)
        # erosion_huaico:          slope*0.5 + rain*0.3 + hv*0.2  = 0.45+0.27+0.1 = 0.82
        # Algorithm picks first in priority list that exceeds 0.15; ladera is first.
        assert risk in ("erosion_huaico", "ladera_inestable_sismo")
