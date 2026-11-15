"""F4: no assumed initial NDVI may be published as a zone measurement."""
import json
from pathlib import Path

import pytest

from sarlab_pipeline.remediation.risk import _build_recovery_scenario


def test_unknown_cause_has_no_borrowed_scenario():
    assert _build_recovery_scenario("causa_por_verificar") is None


@pytest.mark.parametrize("risk", ["incendio_sequia", "erosion_huaico", "estres_hidrico_agricola"])
def test_scenario_contains_relative_gains_only(risk):
    scenario = _build_recovery_scenario(risk)
    assert "baseline_ndvi" not in scenario
    assert scenario["basis"] == "relative_gain_assumption"
    assert scenario["citation_status"] == "por_verificar"
    assert all(set(row) == {"gain_ndvi"} for row in scenario["projected"].values())


PUBLISHED = Path(__file__).resolve().parents[3] / "data/04_published/remediation/ayacucho-huanta.json"


@pytest.mark.skipif(not PUBLISHED.exists(), reason="Actual published data not installed")
def test_no_published_zone_contains_an_absolute_ndvi_scenario():
    for zone in json.loads(PUBLISHED.read_text(encoding="utf-8"))["alerts"]:
        scenario = zone.get("recovery_scenario")
        if scenario:
            assert "baseline_ndvi" not in scenario
            assert all("ndvi" not in row for row in scenario["projected"].values())


@pytest.mark.skipif(not PUBLISHED.exists(), reason="Actual published data not installed")
def test_pdf_omits_unverified_scenario_numbers():
    from sarlab_pipeline.remediation.certificate_pdf import generate_certificate_pdf

    zone = next(zone for zone in json.loads(PUBLISHED.read_text(encoding="utf-8"))["alerts"]
                if zone.get("recovery_scenario"))
    pdf = generate_certificate_pdf({"properties": {"id": zone["alert_id"], "remediation": zone}})
    assert b"No incluido:" in pdf  # content streams are deliberately uncompressed
    assert b"NDVI Supuesto" not in pdf
    assert b"Ganancia relativa NDVI a" not in pdf
