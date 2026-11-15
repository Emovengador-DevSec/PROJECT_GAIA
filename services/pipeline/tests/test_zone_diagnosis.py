"""F1: zone prose must be supported by its measurements, never recipe boilerplate."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sarlab_pipeline.remediation.risk import compute_risk_for_alert


def test_dry_soil_without_fires_never_mentions_fires():
    zone = compute_risk_for_alert(
        {"id": "test-dry", "hv_drop_db": 3.2, "area_ha": 1.0},
        slope_deg=10.0, soil_moisture=0.10, soil_moisture_date="2026-09-16",
        fires_nearby=[], quakes_nearby=[],
    )
    assert zone["risk_id"] == "incendio_sequia"
    for text in (zone["summary"], zone["cause_explanation"], zone["risk_description"]):
        assert "focos" not in text.lower()
        assert "confirma" not in text.lower()
        assert "lluvia" not in text.lower()
        assert "sismo" not in text.lower()
    assert "0,100 m³/m³" in zone["summary"]
    assert "2026-09-16" in zone["summary"]
    assert zone["cause_factor_ids"] == ["soil_moisture_m3m3"]


def test_heat_without_sme2_never_invents_soil_moisture():
    fires = [{"acq_date": datetime.now(UTC).date().isoformat()}]
    zone = compute_risk_for_alert({"hv_drop_db": 4.0}, fires_nearby=fires)
    assert zone["risk_id"] == "incendio_sequia"
    assert "1 focos" in zone["summary"]
    assert "humedad" not in zone["summary"].lower()
    assert "humedad" not in zone["cause_explanation"].lower()
    assert zone["cause_factor_ids"] == ["heat_count"]


def test_erosion_without_rainfall_explains_only_the_measured_slope():
    zone = compute_risk_for_alert({"hv_drop_db": 3.2}, slope_deg=30.0)
    assert zone["risk_id"] == "erosion_huaico"
    assert "30,0°" in zone["summary"]
    assert "lluvia" not in zone["cause_explanation"].lower()
    assert zone["cause_factor_ids"] == ["slope_deg"]


def test_agricultural_stress_requires_both_measured_dry_soil_and_crop_area():
    zone = compute_risk_for_alert({"hv_drop_db": 4.0, "crop_ha": 5.2}, soil_moisture=0.10)
    assert zone["risk_id"] == "estres_hidrico_agricola"
    assert "5,20 ha" in zone["cause_explanation"]
    assert "0,100 m³/m³" in zone["cause_explanation"]
    assert "focos" not in zone["summary"].lower()


def test_seismic_diagnosis_uses_the_quake_that_contributed_to_the_index():
    quakes = [
        {"properties": {"mag": 2.0}, "_distance_km": 1.0},
        {"properties": {"mag": 7.0}, "_distance_km": 5.0},
    ]
    zone = compute_risk_for_alert({"hv_drop_db": 3.2}, slope_deg=20.0, quakes_nearby=quakes)
    assert zone["risk_id"] == "ladera_inestable_sismo"
    assert "Sismo M7,0 a 5,0 km" in zone["cause_explanation"]
    assert "M2" not in zone["summary"]
    assert zone["factors"]["quake_magnitude"] == 7.0


def test_missing_inputs_and_real_zero_values_are_distinct():
    missing = compute_risk_for_alert({})
    assert missing["summary_factor_ids"] == []
    assert missing["cause_factor_ids"] == []
    assert missing["risk_id"] == "causa_por_verificar"
    measured = compute_risk_for_alert({"hv_drop_db": 0.0}, slope_deg=0.0, rain_mm_7d=0.0)
    assert "0,0 dB" in measured["summary"]
    assert "0,0°" in measured["summary"]
    assert "0,0 mm" in measured["summary"]
    assert "humedad" not in measured["summary"].lower()


def test_dry_gate_uses_unrounded_score_for_the_explanation():
    fires = [{"acq_date": datetime.now(UTC).date().isoformat()}]
    zone = compute_risk_for_alert({"hv_drop_db": 4.0}, soil_moisture=0.1501, fires_nearby=fires)
    assert zone["risk_id"] == "incendio_sequia"
    assert "soil_moisture_m3m3" not in zone["cause_factor_ids"]


PUBLISHED = Path(__file__).resolve().parents[3] / "data/04_published/remediation/ayacucho-huanta.json"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="Real published remediation data not installed")
def test_all_published_diagnoses_omit_absent_factors():
    data = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    tokens = {"hv_drop_db": "señal HV", "slope_deg": "Pendiente", "soil_moisture_m3m3": "Humedad",
              "heat_count": "focos", "quake_magnitude": "Sismo", "rain_mm_7d": "Lluvia", "crop_ha": "Cultivo"}
    for zone in data["alerts"]:
        factors = zone["factors"]
        summary = zone["summary"]
        for key, token in tokens.items():
            value = factors.get(key)
            present = value is not None and (
                key not in ("heat_count", "quake_magnitude", "crop_ha") or value > 0
            )
            assert (token in summary) == present, (zone["alert_id"], key, summary)
        assert set(zone["cause_factor_ids"]) <= set(zone["summary_factor_ids"])
        assert zone["risk_description"] == zone["cause_explanation"]
        if not factors.get("heat_count"):
            assert "focos" not in zone["cause_explanation"].lower()
